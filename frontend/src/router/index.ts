import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'home',
      component: () => import('../pages/HomePage.vue'),
    },
    {
      path: '/drug/:id',
      name: 'drug',
      component: () => import('../pages/DrugDetailPage.vue'),
      props: route => ({ drugId: Number(route.params.id) }),
    },
  ],
})

export default router
