<template>
  <q-page class="flex flex-top column">
    <scraper-card :id="id" />
    <q-separator spaced />
    <scraper-runs :id="id" />
  </q-page>
</template>

<script>
import ScraperCard from '../components/ScraperCard.vue';
import ScraperRuns from '../components/ScraperRuns.vue';

export default {
  components: { ScraperCard, ScraperRuns },
  name: 'ScraperPage',
  props: ['id'],
}
</script>
