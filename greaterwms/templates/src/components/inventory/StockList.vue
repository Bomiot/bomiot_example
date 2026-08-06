
<template>
  <div class="q-pa-md">
    <q-table
      :class="$q.dark.isActive ? 'my-sticky-header-last-column-table-dark' : 'my-sticky-header-last-column-table'"
      flat
      bordered
      :rows="rows"
      :columns="columns"
      row-key="index"
      v-model:pagination="pagination"
      separator="cell"
      :no-data-label="t('nodata')"
      :rows-per-page-label="t('per_page')"
      :rows-per-page-options="[30, 50, 200, 1000]"
      :table-style="{ height: screenHeight, width: screenWidth }"
      :card-style="{ backgroundColor: cardBackground }"
      @request="onRequest"
    >
      <template v-slot:top="props">
        <q-btn-group flat>
          <q-btn
            :label="t('refresh')"
            icon="refresh"
            @click="onRequest()"
          >
            <q-tooltip
              class="bg-indigo"
              :offset="[10, 10]"
              content-style="font-size: 12px"
            >{{ t('refreshdata') }}</q-tooltip>
          </q-btn>
        </q-btn-group>
        <q-space />
        <q-input
          dense
          debounce="300"
          color="primary"
          v-model="search"
          @update:model-value="onRequest()"
        >
          <template v-slot:append>
            <q-icon name="search" />
          </template>
        </q-input>
        <q-btn
          flat
          round
          dense
          :icon="props.inFullscreen ? 'fullscreen_exit' : 'fullscreen'"
          @click="props.toggleFullscreen"
        />
      </template>

      <template v-slot:body-cell="props">
        <q-td :props="props">
          {{ props.value || 0 }}
        </q-td>
      </template>

      <template v-slot:pagination>
        {{ t('total') }}{{ pagesNumber }} {{ t('page') }}
        <q-pagination
          v-model="pagination.page"
          :max="pagesNumber"
          input
          debounce="300"
          input-class="text-orange-10"
          @update:model-value="onRequest()"
        />
      </template>
    </q-table>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useQuasar } from 'quasar'
import { useI18n } from 'vue-i18n'
import { get } from 'boot/axios'
import { useTokenStore } from 'stores/token'
import { useLanguageStore } from 'stores/language'
import emitter from 'boot/bus.js'

const { t } = useI18n()
const $q = useQuasar()
const tokenStore = useTokenStore()
const langStore = useLanguageStore()

const columns = computed(() => [
  { name: 'goods_code', required: true, label: t('inventory.goods_code'), align: 'left', field: 'goods_code' },
  { name: 'goods_name', label: t('inventory.goods_name'), field: 'goods_name' },
  { name: 'total_qty', label: t('inventory.total_qty'), field: 'total_qty' },
  { name: 'on_hand_qty', label: t('inventory.on_hand_qty'), field: 'on_hand_qty' },
  { name: 'can_use_qty', label: t('inventory.can_use_qty'), field: 'can_use_qty' },
  { name: 'hold_qty', label: t('inventory.hold_qty'), field: 'hold_qty' },
  { name: 'inspection_qty', label: t('inventory.inspection_qty'), field: 'inspection_qty' },
  { name: 'damage_qty', label: t('inventory.damage_qty'), field: 'damage_qty' },
  { name: 'allocated_qty', label: t('inventory.allocated_qty'), field: 'allocated_qty' },
  { name: 'asn_qty', label: t('inventory.asn_qty'), field: 'asn_qty' },
  { name: 'dn_qty', label: t('inventory.dn_qty'), field: 'dn_qty' },
  { name: 'created_time', label: t('created_time'), field: 'created_time' },
  { name: 'updated_time', label: t('updated_time'), field: 'updated_time' },
])

const token = computed(() => tokenStore.token)
const rows = ref([])
const teamList = ref([])
const departmentList = ref([])
const search = ref('')
const rowsCount = ref(0)

const pagination = ref({
  sortBy: 'updated_time',
  descending: false,
  page: 1,
  rowsPerPage: 30,
  rowsNumber: 30
})

const pagesNumber = computed(() => {
  if (token.value !== '') {
    return Math.ceil(rowsCount.value / pagination.value.rowsPerPage)
  } else {
    return 0
  }
})

const screenHeight = ref(`${$q.screen.height * 0.73}px`)
const screenWidth = ref(`${$q.screen.width * 0.825}px`)
const cardBackground = ref($q.dark.isActive ? '#121212' : '#ffffff')

async function onRequest(props) {
  let requestData = {}
  if (props) {
    requestData = props
  } else {
    requestData.pagination = pagination.value
  }
  await get({
    url: 'core/stock/',
    params: {
      params: JSON.stringify({ data__goods_code__icontains: search.value, data__goods_name__icontains: search.value }),
      page: requestData.pagination.page,
      max_page: requestData.pagination.rowsPerPage
    }
  })
    .then((res) => {
      rows.value = res.results
      rowsCount.value = res.count
      teamList.value = res.team
      departmentList.value = res.department
    })
    .catch((err) => {
      $q.notify({
        type: 'error',
        message: err
      })
      $q.loading.hide()
    }).finally(() => {
      $q.loading.hide()
    })
  pagination.value = requestData.pagination
}

onMounted(() => {
  listenToEvent()
  onRequest()
})

watch(() => $q.dark.isActive, (val) => {
  cardBackground.value = val ? '#121212' : '#ffffff'
})

function listenToEvent() {
  emitter.on('needLogin', (payload) => {
    if (payload) {
      rows.value = []
      teamList.value = []
      search.value = ''
      rowsCount.value = 0
    }
  })
}

watch(() => langStore.langData, (val) => {
  if (val) {
    onRequest()
  }
})
</script>
