
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
          @update:model-value="onRequest()">
          <template v-slot:append>
            <q-icon name="search" @click="onRequest()"/>
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
          <div v-if="props.col.name === 'action'">
            <q-btn
              round
              flat
              icon="pallet"

              @click="createData(props.rowIndex)"
            >
              <q-tooltip
                class="bg-indigo"
                :offset="[10, 10]"
                content-style="font-size: 12px"
              >{{ t('asn.location') }}</q-tooltip>
            </q-btn>
          </div>
          <div v-else>
            {{ props.value }}
          </div>
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
  <q-dialog v-model="formData">
    <q-card class="shadow-24">
      <q-bar class="bg-light-blue-10 text-white rounded-borders" style="height: 50px">
        <div class="text-h6">{{ t(`asn.${mode}`) }}</div>
      </q-bar>

      <q-card-section style="max-height: 325px; width: 400px" class="scroll">
        <q-input
          dense
          outlined
          square
          debounce="500"
          v-model="data.qty"
          :label="t('asn.shelving_qty')"
          style="margin-bottom: 5px"
        >
          <template v-slot:before>
            <q-select
              transition-show="jump-up"
              transition-hide="jump-up"
              dense
              outlined
              square
              use-input
              hide-selected
              fill-input
              stack-label
              v-model="data.selected"
              :label="t('asn.bin')"
              :options="binOptions"
              @focus="getFocus(index)"
              @input-value="setBinOptions"
            >
              <template v-slot:no-option>
                <q-item>
                  <q-item-section class="text-grey">No results</q-item-section>
                </q-item>
              </template>
              <template v-slot:option="scope">
                <q-item v-bind="scope.itemProps">
                  <q-item-section>
                    <q-item-label>{{ scope.opt.label }}</q-item-label>
                    <q-item-label caption>{{ scope.opt.name }}</q-item-label>
                  </q-item-section>
                </q-item>
              </template>
              <template v-if="data.selected" v-slot:append>
                <q-icon name="cancel" @click.stop="data.selected = ''" class="cursor-pointer" />
              </template>
            </q-select>
          </template>
        </q-input>
      </q-card-section>
      <div style="float: right; padding: 15px 15px 15px 0">
        <q-btn flat :label="t('cancel')" color="primary" v-close-popup @click="cancelSubmit()" />
        <q-btn flat :label="t('submit')" color="primary" v-close-popup @click="submitData(mode)" />
      </div>
    </q-card>
  </q-dialog>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useQuasar } from 'quasar'
import { useI18n } from 'vue-i18n'
import { get, post } from 'boot/axios'
import { useTokenStore } from 'stores/token'
import { useLanguageStore } from 'stores/language'
import emitter from 'boot/bus.js'

const { t } = useI18n()
const $q = useQuasar()
const tokenStore = useTokenStore()
const langStore = useLanguageStore()

const columns = computed(() => [
  { name: 'asn_id', required: true, label: t('asn.asn_id'), align: 'left', field: 'asn_id' },
  { name: 'status', label: t('asn.status'), field: 'status' },
  { name: 'goods_code', label: t('asn.goods_code'), field: 'goods_code' },
  { name: 'goods_name', label: t('asn.goods_name'), field: 'goods_name' },
  { name: 'asn_qty', label: t('asn.asn_qty'), field: 'asn_qty' },
  { name: 'shelving_qty', label: t('asn.shelving_qty'), field: 'shelving_qty' },
  { name: 'created_time', label: t('created_time'), field: 'created_time' },
  { name: 'updated_time', label: t('updated_time'), field: 'updated_time' },
  { name: 'action', label: t('action'), align: 'right' }
])

const token = computed(() => tokenStore.token)
const rows = ref([])
const search = ref('')
const formData = ref(false)
const data = ref({})
const binOptions = ref([])
const focusIndex = ref('')
const binSearch = ref('')
const mode = ref('shelving')
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
    url: 'core/asn/detail/',
    params: {
      params: JSON.stringify({ data__asn_id__icontains: search.value }),
      page: requestData.pagination.page,
      max_page: requestData.pagination.rowsPerPage
    }
  })
    .then((res) => {
      rows.value = res.results
      rowsCount.value = res.count
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

function createData(e) {
  mode.value = 'update'
  data.value = { ...rows.value[e], selected: '' }
  data.value.process = 'shelving'
  formData.value = true
}

function cancelSubmit() {
  formData.value = false
  data.value = {}
}

async function submitData(e) {
  await post(`core/asn/detail/${e}/`, data.value)
  .then(() => {
    onRequest()
    cancelSubmit()
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
}

function getFocus(index) {
  focusIndex.value = index
}

function setBinOptions(value) {
  setTimeout(() => {
    binSearch.value = value
  }, 260)
}

onMounted(() => {
  listenToEvent()
  onRequest()
})

watch(() => binSearch.value, (val) => {
  if (val.includes("'") || val === '') {
    return
  }
  get({
    url: 'core/bin/',
    params: {
      params: JSON.stringify({
        data__name__icontains: val,
        data__property__icontains: val,
        data__empty__exact: 0,
        data__lock__exact: 0
      }),
      page: 1,
      max_page: 5
    }
  })
    .then((res) => {
      binOptions.value = res.results.map(item => {
        return {
          name: item.property,
          label: item.name
        }
      })
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
})

watch(() => $q.dark.isActive, (val) => {
  cardBackground.value = val ? '#121212' : '#ffffff'
})

function listenToEvent() {
  emitter.on('needLogin', (payload) => {
    if (payload) {
      rows.value = []
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
