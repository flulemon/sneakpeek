<template>
  <q-page>
    <scraper-ide-component v-model="draftScraper.config" :enable-save-btn="true" @save="onSave" />
    <q-dialog v-model="showSaveDialog">
      <q-card class="save-dialog">
        <q-card-section>
          <div class="text-h6">Save Scraper</div>
        </q-card-section>
        <q-card-section class="q-pt-none">
          <q-input v-model="draftScraper.name" label="Name" dense />
          <q-select v-model="draftScraper.schedule" label="Schedule" :options="schedules" dense class="q-pt-md" />
          <q-input v-model="draftScraper.schedule_crontab" label="Crontab" v-if="draftScraper.schedule === 'crontab'" dense class="q-pt-md" />
          <q-select v-model="draftScraper.priority" label="Priority" :options="priorities" dense class="q-pt-md" />
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat label="Cancel" v-close-popup />
          <q-btn label="Save" color="positive" :loading="saveLoading" @click="saveScraper" />
        </q-card-actions>
      </q-card>
    </q-dialog>
  </q-page>
</template>
<script>
import { format } from 'quasar';
import { createScraper, getPriorities, getSchedules } from "../api.js";
import ScraperIdeComponent from '../components/ScraperIdeComponent.vue';

const { capitalize } = format;

export default {
  name: "ScraperIde",
  components: { ScraperIdeComponent },
  data() {
    return {
      loading: false,
      error: false,
      showSaveDialog: false,
      draftScraper: {
        name: "",
        schedule: "inactive",
        priority: 0,
        handler: "dynamic_scraper",
        config: {}
      },
      schedules: [],
      priorities: [],
      saveLoading: false,
    }
  },
  created() {
    this.loading = true;
    Promise.all([
      getSchedules().then(data => this.schedules = data.map(this.makeScheduleOption)),
      getPriorities().then(data => this.priorities = data.map(this.makePriorityOption)),
    ])
    .then(this.prettifyScraperParamsLabels)
    .catch((error) => this.$q.notify({
      message: `Error occured, plese refresh the page: ${error}`,
      color: "negative",
    }))
    .finally(() => this.loading = false);
  },
  methods: {
    makeScheduleOption(item) {
      return {
        label: item.split("_").map(capitalize).join(" "),
        value: item,
      };
    },
    makePriorityOption(item) {
      return {
        label: capitalize(item.name),
        value: item.value,
      };
    },
    onSave(config) {
      this.draftScraper.config = config;
      this.prettifyScraperParamsLabels();
      this.showSaveDialog = true;
    },
    prettifyScraperParamsLabels() {
      const schedule = this.schedules.filter(x => x.value === this.draftScraper.schedule)[0];
      this.draftScraper.schedule = schedule || this.draftScraper.schedule;

      const priority = this.priorities.filter(x => x.value === this.draftScraper.priority)[0];
      this.draftScraper.priority = priority || this.draftScraper.priority;
    },
    saveScraper() {
      const payload = {
        name: this.draftScraper.name,
        handler: this.draftScraper.handler,
        schedule: this.draftScraper.schedule.value || this.draftScraper.schedule,
        priority: this.draftScraper.priority.value == 0 ? 0 : (this.draftScraper.priority.value || this.draftScraper.priority),
        schedule_crontab: this.draftScraper.schedule_crontab,
        config: this.draftScraper.config,
      }
      this.saveLoading = true;
      createScraper(payload)
        .then((result) => {
          this.$q.notify({
            message: `Successfully created new scraper`,
            color: "positive",
          });
          this.$router.push({ name: 'ScraperPage', params: {id: result.id }});
        })
        .catch(error => this.$q.notify({
            message: `Failed to create new scraper: ${error}`,
            color: "negative",
          }))
        .finally(() => this.saveLoading = false);
    }
  }
};
</script>
<style>
.save-dialog {
  min-width: 500px;
}
</style>
