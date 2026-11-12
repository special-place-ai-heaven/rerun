// Imported first by the engine entry (src/cli/bin.ts): ES modules run in import order, so the key
// descriptor is read and closed before any other module can call env().
import { takeKeyFromDescriptor } from './env.js'

takeKeyFromDescriptor()
