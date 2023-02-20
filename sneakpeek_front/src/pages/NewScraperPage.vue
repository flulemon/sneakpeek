<template>
  <q-page class="flex flex-top column q-py-md q-px-xl">
    <div class="text-h6">
      Add new scraper
    </div>
    <q-separator spaced />
    <scraper-edit-form />
  </q-page>
</template>

<script>
import ScraperEditForm from '../components/ScraperEditForm.vue';

export default {
  components: { ScraperEditForm },
  name: 'NewScraperPage',
}
</script>
