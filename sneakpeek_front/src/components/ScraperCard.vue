<template>
  <div>
    <transition appear enter-active-class="animated fadeIn" leave-active-class="animated fadeOut">
      <div v-if="!error && !loading" class="q-py-md q-px-xl">
        <div class="flex row q-mb-md">
          <div class="text-h6">
            {{ scraper.name }}
          </div>
          <q-space />
          <div class="flex row">
            <q-btn class="q-mr-sm" icon="fa-solid fa-play" label="Run" size="sm" color="positive"
                   :loading="enqueueLoading" @click="enqueueRun" />
            <q-btn :icon="showConfiguration ? 'fa-solid fa-chevron-up': 'fa-solid fa-chevron-down'"
                  :label="showConfiguration ? 'Close config': 'Open config'"
                  @click="showConfiguration = !showConfiguration"
                  size="sm" color="secondary" class="text-black"  />
          </div>
        </div>
        <q-expansion-item v-model="showConfiguration" hide-expand-icon header-style="display: none;">
          <scraper-edit-form v-model="scraper" />
        </q-expansion-item>
      </div>
    </transition>
    <transition appear enter-active-class="animated fadeIn" leave-active-class="animated fadeOut">
      <div v-if="error && !loading">
        <div class="text-h6 text-center">
          Failed to load scraper. Try to refresh. <br />
          {{ error }}
        </div>
      </div>
    </transition>
    <q-inner-loading :showing="loading">
      <q-spinner-grid size="50px" color="primary" />
    </q-inner-loading>
  </div>
</template>

<script>
import useQuasar from 'quasar/src/composables/use-quasar.js';
import { enqueueScraper, getScraper } from "../api.js";
import ScraperEditForm from './ScraperEditForm.vue';

export default {
  name: 'ScraperCard',
  props: ['id'],
  components: { ScraperEditForm },
  data() {
    return {
      loading: false,
      error: false,
      scraper: {},
      $q: useQuasar(),
      showConfiguration: false,
      enqueueLoading: false,
    }
  },
  created() {
    this.loading = true;
    getScraper(this.id)
      .then(item => this.scraper = item)
      .catch(error => this.error = error)
      .finally(() => this.loading = false);
  },
  methods: {
    enqueueRun() {
      this.enqueueLoading = true;
      enqueueScraper(this.scraper.id)
        .then(() => this.$q.notify({
          message: "Successfully enqueued scraper run",
          color: "positive"
        }))
        .catch(error => this.$q.notify({
          message: `Failed to enqueue scraper run: ${error}`,
          color: "negative"
        }))
        .finally(() => this.enqueueLoading = false);
    }
  }
}
</script>
