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
      path: "/results",
      name: "results",
      component: () => import("@/views/ResultsPage.vue"),
    },
    {
      path: "/paper",
      name: "paper",
      component: () => import("@/views/PaperPage.vue"),
    },
    {
      path: "/paper/sources",
      name: "paper-sources",
      component: () => import("@/views/PaperSourcesView.vue"),
    },
    {
      path: "/hub",
      component: () => import("@/layouts/HubLayout.vue"),
      redirect: "/hub/dashboard",
      children: [
        {
          path: "dashboard",
          name: "hub-dashboard",
          component: () => import("@/views/hub/DashboardView.vue"),
        },
        {
          path: "library",
          name: "hub-library",
          component: () => import("@/views/hub/FrameworkLibraryView.vue"),
        },
        {
          path: "library/extract",
          name: "hub-extract",
          component: () => import("@/views/hub/ExtractFrameworkView.vue"),
        },
        {
          path: "projects",
          name: "hub-projects",
          component: () => import("@/views/hub/ProjectsView.vue"),
        },
        {
          path: "projects/new",
          name: "hub-projects-new",
          component: () => import("@/views/hub/CreateProjectView.vue"),
        },
        {
          path: "projects/:id",
          name: "hub-project-detail",
          component: () => import("@/views/hub/ProjectDetailView.vue"),
        },
        {
          path: "projects/:id/result",
          name: "hub-project-result",
          component: () => import("@/views/hub/ResultView.vue"),
        },
        {
          path: "settings",
          name: "hub-settings",
          component: () => import("@/views/hub/SettingsView.vue"),
        },
      ],
    },  
  ],
});

export default router;
