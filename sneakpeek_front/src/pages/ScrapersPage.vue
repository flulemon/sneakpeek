<template>
  <q-page class="flex flex-center" style="width: 100%;">
    <q-table :rows="rows" :columns="columns" row-key="id"
             style="width: 100%; height: 100vh;" virtual-scroll hide-bottom
             :loading="loading" :rows-per-page-options="[0]">
      <template v-slot:top>
        <q-text>
          <div class="text-h6">Scrapers</div>
        </q-text>
        <q-space />
        <q-input borderless dense debounce="300" color="primary" v-model="filter">
          <template v-slot:append>
            <q-icon name="search" />
          </template>
        </q-input>
      </template>

      <template v-slot:body-cell-priority="props">
        <q-td :props="props">
          <priority-chip :value="props.value" size="sm" />
        </q-td>
      </template>

      <template v-slot:body-cell-schedule="props">
        <q-td :props="props">
          <schedule-chip size="sm" color="primary" text-color="white" :value="props.value" />
        </q-td>
      </template>

      <template v-slot:body-cell-actions="props">
        <q-td :props="props">
            <q-btn flat round icon="fa-solid fa-edit" size="sm"
                :to="$router.resolve({ name: 'ScraperPage', params: { id: props.value.id } })" />
        </q-td>
      </template>

    </q-table>
  </q-page>
</template>

<script>
import { getScrapers } from "../api.js";
import PriorityChip from '../components/PriorityChip.vue';
import ScheduleChip from '../components/ScheduleChip.vue';

export default {
  components: { PriorityChip, ScheduleChip },
  name: 'ScrapersPage',
  data() {
    return {
      loading: false,
      error: false,
      columns: [
        { name: 'id', label: 'ID', field: 'id', align: 'left' },
        { name: 'name', label: 'Name', field: 'name', align: 'left'},
        { name: 'schedule', label: 'Schedule', field: 'schedule', align: 'center' },
        { name: 'priority', label: 'Priority', field: 'schedule_priority', align: 'center' },
        { name: 'actions', label: 'Actions', field: row => row, align: 'right' },
      ],
      rows: []
    }
  },
  created() {
    this.loading = true;
    getScrapers()
      .then((data) => this.rows = data)
      .catch((error => this.error = error))
      .finally(() => this.loading = false);
  }
}
</script>
