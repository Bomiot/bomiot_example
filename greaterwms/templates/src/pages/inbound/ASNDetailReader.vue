<template>
  <q-page class="flex flex-top">
    <ASNDetail />
  </q-page>
</template>

<script setup>
import { onBeforeUnmount, onMounted, watch, ref } from 'vue'
import { useMeta, useQuasar } from "quasar"
import ASNDetail from "components/inbound/ASNDetail.vue"


const $q = useQuasar()


const darkShow = ref(false)
const title = ref('')
const description = ref('')
const keywords = ref('')

useMeta(() => {
  return {
    title: title.value,
    meta: {
        description: { name: 'description', content: description.value },
        keywords: { name: 'keywords', content: keywords.value },
      }
    }
  })


onMounted (() => {
})


onBeforeUnmount(() => {
})


watch(() => $q.dark.isActive, val => {
  darkShow.value = val
})

</script>
