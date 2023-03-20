<template>
  <q-page class="flex flex-top column q-py-md q-px-xl">
    <scraper-card :id="id" />
    <q-separator spaced />
    <scraper-jobs :id="id" />
  </q-page>
</template>

<script>
import ScraperCard from '../components/ScraperCard.vue';
import ScraperJobs from '../components/ScraperJobs.vue';

export default {
  components: { ScraperCard, ScraperJobs },
  name: 'ScraperPage',
  props: ['id'],
}
</script>
