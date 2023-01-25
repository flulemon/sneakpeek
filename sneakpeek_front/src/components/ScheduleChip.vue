<template>
  <q-chip :label="label" v-bind="$attrs" />
</template>
<script>
import { format } from 'quasar';
const { capitalize } = format;

export default {
  name: "ScheduleChip",
  props: ["value"],
  data() {
    return {
      label: "Unknown",
    };
  },
  created() {
    this.label = this.value.split("_").map(capitalize).join(" ");
  }
}
</script>
