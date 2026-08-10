import { createRouter, createWebHistory } from "vue-router";
import { useAuthStore } from "@/store/authStore";

const PUBLIC_PATHS = ["/login", "/register"];

const devOnlyRoutes = import.meta.env.DEV
  ? [
      {
        path: "/style-guide",
        name: "style-guide",
        component: () => import("@/views/StyleGuideView.vue"),
      },
    ]
  : [];

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    ...devOnlyRoutes,
    {
      path: "/",
      redirect: "/hub/dashboard",
    },
    {
      path: "/login",
      name: "login",
      component: () => import("@/views/LoginView.vue"),
    },
    {
      path: "/register",
      name: "register",
      component: () => import("@/views/RegisterView.vue"),
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
          path: "projects/:id/mapping",
          name: "hub-project-mapping",
          component: () => import("@/views/hub/FieldMappingView.vue"),
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

router.beforeEach(async to => {
  const authStore = useAuthStore();

  if (!authStore.isReady) {
    await authStore.checkSession();
  }

  const isPublicPath = PUBLIC_PATHS.includes(to.path);

  if (!isPublicPath && !authStore.isAuthenticated) {
    return "/login";
  }

  if (isPublicPath && authStore.isAuthenticated) {
    return "/hub/dashboard";
  }
});

export default router;
