<template>
  <q-chip :color="color" :text-color="textColor" :label="label" v-bind="$attrs"  />
</template>
<script>
export default {
  name: "PriorityChip",
  props: ["value"],
  data() {
    return {
      label: "Unknown",
      color: "secondary",
      textColor: "black",
    };
  },
  created() {
    switch (this.value) {
        case 0:
          this.label = "Utmost";
          this.color = "accent";
          this.textColor = "white";
          break;
        case 1:
          this.label = "High";
          this.color = "warning";
          this.textColor = "black";
          break;
        case 2:
          this.label = "Normal";
          this.color = "primary";
          this.textColor = "white";
          break;
      }
  }
}
</script>
