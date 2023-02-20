<template>
  <q-form>
    <q-input readonly v-model="draftScraper.id" label="ID" v-if="mode === 'edit'" />
    <q-input v-model="draftScraper.name" label="Name" />
    <q-select v-model="draftScraper.schedule" label="Schedule" :options="schedules" emit-value />
    <q-input v-model="draftScraper.schedule_crontab" label="Crontab" v-if="draftScraper.schedule === 'crontab'" />
    <q-select v-model="draftScraper.schedule_priority" label="Priority" :options="priorities" emit-value />
    <q-select v-model="draftScraper.handler" label="Handler" :options="handlers" emit-value />
    <JsonEditorVue v-model="draftScraper.config" mode="text" :mainMenuBar="false" :statusBar="false"
                    class="q-py-md" :class="$q.dark.isActive ? 'jse-theme-dark': ''" />
    <div class="flex justify-end">
      <q-btn class="q-mr-sm" icon="fa-solid fa-trash" label="Delete" size="sm" color="negative"
             v-if="mode === 'edit'" @click="deleteDialog = true" />
      <q-btn class="q-mr-sm" icon="fa-solid fa-save" label="Save" size="sm" color="positive"
              @click="saveScraper" :loading="saveLoading"  />
    </div>

    <q-dialog v-model="deleteDialog" persistent>
      <q-card>
        <q-card-section class="row items-center text-h6">
          Are you sure you want to delete scraper '{{ draftScraper.name }}'?
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat label="Cancel" color="white" v-close-popup />
          <q-btn label="Delete" color="negative" @click="deleteScraper" :loading="deleteLoading" />
        </q-card-actions>
      </q-card>
    </q-dialog>
  </q-form>
</template>
<script>
import JsonEditorVue from 'json-editor-vue';
import { extend, format } from 'quasar';
import useQuasar from 'quasar/src/composables/use-quasar.js';
import 'vanilla-jsoneditor/themes/jse-theme-dark.css';
import { createOrUpdateScraper, deleteScraper, getPriorities, getSchedules, getScraperHandlers } from "../api.js";

const { capitalize } = format;

export default {
  name: "ScraperEditForm",
  components: {JsonEditorVue},
  props: ["modelValue"],
  emits: ['update:modelValue'],
  data() {
    return {
      mode: "new",
      $q: useQuasar(),

      loading: false,
      error: false,

      defaultScraper: {
        name: "",
        schedule: "inactive",
        priority: 0,
        handler: "",
        config: {}
      },
      draftScraper: {},

      handlers: [],
      schedules: [],
      priorities: [],

      saveLoading: false,
      saveError: false,

      deleteDialog: false,
      deleteLoading: false,
      deleteError: false,
    }
  },
  created() {
    this.draftScraper = this.modelValue || this.defaultScraper;
    this.mode = this.draftScraper.id == null ? 'new' : 'edit';
    this.loading = true;
    Promise.all([
      getScraperHandlers().then(data => this.handlers = data),
      getSchedules().then(data => this.schedules = data.map(this.makeScheduleOption)),
      getPriorities().then(data => this.priorities = data.map(this.makePriorityOption)),
    ])
    .then(this.prettifyScraperParamsLabels)
    .catch((error => this.error = error))
    .finally(() => this.loading = false);
  },
  watch: {
    modelValue: {
      deep: true,
      handler(val) {
        this.draftScraper = extend(true, {}, val || this.defaultScraper);
        this.prettifyScraperParamsLabels();
      }
    }
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
    prettifyScraperParamsLabels() {
      const schedule = this.schedules.filter(x => x.value === this.draftScraper.schedule)[0];
      this.draftScraper.schedule = schedule || this.draftScraper.schedule;

      const priority = this.priorities.filter(x => x.value === this.draftScraper.schedule_priority)[0];
      this.draftScraper.schedule_priority = priority || this.draftScraper.schedule_priority;
    },
    saveScraper() {
      if (typeof this.draftScraper.config === 'string' || this.draftScraper.config instanceof String) {
        this.draftScraper.config = JSON.parse(this.draftScraper.config);
      }
      const payload = {
        id: this.draftScraper.id,
        name: this.draftScraper.name,
        handler: this.draftScraper.handler,
        schedule: this.draftScraper.schedule,
        schedule_priority: this.draftScraper.schedule_priority,
        schedule_crontab: this.draftScraper.schedule_crontab,
        config: this.draftScraper.config,
      }
      this.saveLoading = true;
      createOrUpdateScraper(payload)
        .then((result) => {
          this.$emit('update:modelValue', result);
          this.$q.notify({
            message: `Successfully ${mode === 'edit' ? 'updated' : 'created'} scraper configuration`,
            color: "positive",
          });
          if (this.mode === 'edit') {
            this.$router.push({ name: 'ScraperPage', params: {id: result.id }});
          }
        })
        .catch(error => this.$q.notify({
            message: `Failed to update scraper configuration: ${error}`,
            color: "negative",
          }))
        .finally(() => this.saveLoading = false);
    },
    deleteScraper() {
      this.deleteLoading = true;
      deleteScraper(this.draftScraper.id)
        .then((result) => {
          this.deleteDialog = false;
          this.$q.notify({
            message: `Successfully deleted scraper '${result.name}'`,
            color: "positive",
          });
          this.$router.push({ name: 'ScrapersPage' });
        })
        .catch(error => this.$q.notify({
            message: `Failed to delete scraper '${this.draftScraper.name}': ${error}`,
            color: "negative",
          }))
        .finally(() => this.deleteLoading = false);
    }
  }
}
</script>
<style>
.jse-main {
  max-height: 400px!important;
}
</style>
