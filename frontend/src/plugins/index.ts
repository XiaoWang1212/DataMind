/**
 * plugins/index.ts
 *
 * Automatically included in `./src/main.ts`
 */

// Types
import type { App } from "vue";

// Plugins
import router from "@/router";
import pinia from "@/store";
import i18n from "./i18n";
import vuetify from "./vuetify";

export function registerPlugins(app: App) {
  app.use(pinia);
  app.use(router);
  app.use(i18n);
  app.use(vuetify);
}
