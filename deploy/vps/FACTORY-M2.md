# M2 proof on the dev engine

The exact lines the owner runs, in order, from the clone on the server (rerun#60). Every `sudo` line is its own block.
The dev engine key is never printed. Status shows one PASS/FAIL row per test with names and ids only.
Step 6 (`setup`) creates the dev engine's two stage coworkers, `challenge` (model `stub-fast`) and `challenge-hold` (model `stub-hold`), and keeps their ids in the runner volume; `tools/factory/runner.json` stays a template with no ids.

## 1. Update the clone

```sh
git pull
```

## 2. Dev engine key (once; skipped if the file exists)

```sh
[ -e deploy/vps/.env ] || (umask 077; printf 'RERUN_DEV_ENGINE_KEY=%s\n' "$(openssl rand -hex 32)" > deploy/vps/.env)
```

## 3. Start the dev engine

```sh
sudo docker compose -f deploy/vps/dev-engine.yml up -d
```

## 4. Start the stub model

```sh
sudo docker compose -f deploy/vps/stub-model.yml up -d
```

## 5. Start the runner

The runner needs to be up for step 6, since the key reaches only that container.

```sh
sudo docker compose -f deploy/vps/factory-runner.yml up -d
```

## 6. Set up the dev engine (once; safe to repeat)
Run inside the runner container; the key is read from its environment and never echoed. It registers the stub as the dev engine's `custom` connection and default, creates or reuses the two stage coworkers, writes their ids to `/state/runner-state.json`, and creates the triggers. A second run creates nothing.

```sh
sudo docker compose -f deploy/vps/factory-runner.yml exec -T factory-runner python3 /app/runner_loop.py setup
```

Until this has run, the runner stays up and logs `waiting for setup`; it starts working by itself within 10 seconds of the ids being written.

## 7. R1: fire one stage

```sh
sudo docker compose -f deploy/vps/factory-runner.yml exec -T factory-runner python3 /app/runner_loop.py enqueue r1 challenge
```

Wait 2 minutes, then:

```sh
sudo sh deploy/vps/factory-status.sh
```

## 8. R2: a deliberately long run, cancelled

```sh
sudo docker compose -f deploy/vps/factory-runner.yml exec -T factory-runner python3 /app/runner_loop.py enqueue r2 challenge-hold
```

Wait 3 minutes (the `challenge-hold` stage has its own 120 s run limit in `runner.json`; the stub would hold it for 1800 s, so only the runner can end it), then:

```sh
sudo sh deploy/vps/factory-status.sh
```

## 9. R3: restart the dev engine in the middle of a stage

```sh
sudo docker compose -f deploy/vps/factory-runner.yml exec -T factory-runner python3 /app/runner_loop.py enqueue r3 challenge-hold
```

Wait 20 seconds, then restart the engine:

```sh
sudo docker compose -f deploy/vps/dev-engine.yml restart
```

Wait 90 seconds (the runner sees the `error` row and fires the stage again once), then:

```sh
sudo sh deploy/vps/factory-status.sh
```

## 10. R4: remove and start the runner in the middle of a job

```sh
sudo docker compose -f deploy/vps/factory-runner.yml exec -T factory-runner python3 /app/runner_loop.py enqueue r4 challenge-hold
```

Wait 20 seconds, then remove the runner container (its ledger volume stays):

```sh
sudo docker compose -f deploy/vps/factory-runner.yml rm -sf factory-runner
```

```sh
sudo docker compose -f deploy/vps/factory-runner.yml up -d
```

Wait for the run to end (or be cancelled), then:

```sh
sudo sh deploy/vps/factory-status.sh
```

## R5

R5: checked separately by the owner.

## R6

The R6 row says "for a stage with no tools": the stub returns no tool calls, no compaction and no delegate children,
so it proves only that the runner fires stage runs and nothing else.

## Teardown

```sh
sudo docker compose -f deploy/vps/factory-runner.yml down -v
```

```sh
sudo docker compose -f deploy/vps/stub-model.yml down -v
```

```sh
sudo docker compose -f deploy/vps/dev-engine.yml down -v
```
