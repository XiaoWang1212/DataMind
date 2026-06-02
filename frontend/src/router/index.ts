import { createRouter, createWebHistory } from "vue-router";

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: "/",
      name: "home",
      component: () => import("@/views/HomePage.vue"),
    },
    {
      path: "/tutorial",
      name: "tutorial",
      component: () => import("@/views/TutorialPage.vue"),
    },
    {
      path: "/workflow",
      name: "workflow",
      component: () => import("@/views/WorkflowPage.vue"),
    },
    {
      path: "/sidebar",
      name: "sidebar",
      component: () => import("@/components/Sidebar.vue"),
    },
    {
      path: "/results",
      name: "results",
      component: () => import("@/views/ResultsPage.vue"),
    },
    {
      path: "/pycaret",
      name: "pycaret",
      component: () => import("@/views/PyCaretTestPage.vue"),
    }
  ],
});

export default router;
