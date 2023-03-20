
const routes = [
  {
    name: 'Homepage',
    path: '/',
    component: () => import('layouts/MainLayout.vue'),
    children: [
      { name: 'ScrapersPage', path: '', component: () => import('src/pages/ScrapersPage.vue') },
      { name: 'NewScraperPage', path: 'new', component: () => import('src/pages/NewScraperPage.vue') },
      { name: 'ScraperPage', path: 'scraper/:id', component: () => import('src/pages/ScraperPage.vue'), props: true },
    ]
  },

  // Always leave this as last one,
  // but you can also remove it
  {
    path: '/:catchAll(.*)*',
    component: () => import('pages/ErrorNotFound.vue')
  }
]

export default routes
