<template>
  <q-form>
    <q-input readonly v-model="draftScraper.id" label="ID" v-if="mode === 'edit'" />
    <q-input v-model="draftScraper.name" label="Name" :readonly="isReadOnly" />
    <q-select v-model="draftScraper.schedule" label="Schedule" :options="schedules" :readonly="isReadOnly" />
    <q-input v-model="draftScraper.schedule_crontab" label="Crontab" v-if="draftScraper.schedule === 'crontab'" :readonly="isReadOnly" />
    <q-select v-model="draftScraper.priority" label="Priority" :options="priorities" :readonly="isReadOnly" />
    <q-select v-model="draftScraper.handler" label="Handler" :options="handlers" :readonly="isReadOnly" />
    <scraper-ide-component v-model="draftScraper.config" v-if="draftScraper.handler === 'dynamic_scraper'" />
    <JsonEditorVue v-else v-model="draftScraper.config" mode="text" :mainMenuBar="false" :statusBar="false"
                    class="q-py-md" :class="$q.dark.isActive ? 'jse-theme-dark': ''" :readOnly="isReadOnly" />
    <div class="flex justify-end">
      <q-btn class="q-mr-sm" icon="fa-solid fa-trash" label="Delete" size="sm" color="negative"
             @click="deleteDialog = true" v-if="mode === 'edit' && !isReadOnly"  />
      <q-btn class="q-mr-sm" icon="fa-solid fa-save" label="Save" size="sm" color="positive"
              @click="saveScraper" :loading="saveLoading" v-if="!isReadOnly"   />
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
import { createScraper, deleteScraper, getPriorities, getSchedules, getScraperHandlers, isReadOnly, updateScraper } from "../api.js";
import ScraperIdeComponent from './ScraperIdeComponent.vue';

const { capitalize } = format;

export default {
  name: "ScraperEditForm",
  components: {JsonEditorVue, ScraperIdeComponent},
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

      isReadOnly: false,
    }
  },
  created() {
    isReadOnly().then(result => {this.isReadOnly = result;});
    this.draftScraper = this.modelValue || JSON.parse(JSON.stringify(this.defaultScraper));
    this.mode = this.draftScraper.id == null ? 'new' : 'edit';
    this.loading = true;
    Promise.all([
      getScraperHandlers().then(data => this.handlers = data),
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
  watch: {
    modelValue: {
      deep: true,
      handler(val) {
        this.draftScraper = extend(true, {}, val || JSON.parse(JSON.stringify(this.defaultScraper)));
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

      const priority = this.priorities.filter(x => x.value === this.draftScraper.priority)[0];
      this.draftScraper.priority = priority || this.draftScraper.priority;
    },
    saveScraper() {
      if (typeof this.draftScraper.config === 'string' || this.draftScraper.config instanceof String) {
        this.draftScraper.config = JSON.parse(this.draftScraper.config);
      }
      const payload = {
        id: this.draftScraper.id,
        name: this.draftScraper.name,
        handler: this.draftScraper.handler,
        schedule: this.draftScraper.schedule.value || this.draftScraper.schedule,
        priority: this.draftScraper.priority.value == 0 ? 0 : (this.draftScraper.priority.value || this.draftScraper.priority),
        schedule_crontab: this.draftScraper.schedule_crontab,
        config: this.draftScraper.config,
      }
      this.saveLoading = true;
      const method = this.draftScraper.id ? updateScraper : createScraper;
      method(payload)
        .then((result) => {
          this.$emit('update:modelValue', result);
          this.prettifyScraperParamsLabels();
          this.$q.notify({
            message: `Successfully ${this.mode === 'edit' ? 'updated' : 'created'} scraper configuration`,
            color: "positive",
          });
          if (this.mode === 'new') {
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
