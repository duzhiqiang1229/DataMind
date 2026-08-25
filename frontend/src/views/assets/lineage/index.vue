<template>
  <div class="lineage-page">
    <el-card shadow="never">
      <template #header>
        <div class="header">
          <div><div class="title">运行血缘</div><div class="subtitle">按真实上下游关系分层展示调度任务产生的数据流向</div></div>
          <el-tag type="success" effect="plain">自动采集</el-tag>
        </div>
      </template>

      <div class="toolbar">
        <el-input v-model="keyword" clearable :prefix-icon="Search" placeholder="搜索上游或下游表" @clear="loadLineage" @keyup.enter="loadLineage" />
        <el-button type="primary" @click="loadLineage">查询</el-button>
        <el-button :icon="Refresh" @click="resetView">重置视图</el-button>
      </div>

      <div class="lineage-overview">
        <div class="overview-identity"><span class="overview-label">运行血缘概览</span><strong>{{ nodeCount }} 个物理表</strong><span>来自成功调度任务的实际运行记录</span></div>
        <div class="overview-stat"><span>关系数</span><strong>{{ total }}</strong></div>
        <div class="overview-stat source"><span>源表</span><strong>{{ lineageStats.sources }}</strong></div>
        <div class="overview-stat middle"><span>中间表</span><strong>{{ lineageStats.intermediates }}</strong></div>
        <div class="overview-stat target"><span>目标表</span><strong>{{ lineageStats.targets }}</strong></div>
        <div class="overview-stat"><span>涉及任务</span><strong>{{ lineageStats.tasks }}</strong></div>
        <div class="overview-stat"><span>最近产生</span><strong class="latest-time">{{ formatShortTime(lineageStats.latest) }}</strong></div>
      </div>

      <div class="flow-heading">
        <div><strong>数据流向</strong><span>节点按真实上下游拓扑分层，点击表节点查看运行关系</span></div>
        <div class="flow-actions">
          <div class="flow-legend"><i class="source"></i>源表<i class="middle"></i>中间表<i class="target"></i>目标表</div>
          <el-button v-if="selectedNode" size="small" @click="clearFocus">取消聚焦</el-button>
          <el-button-group>
            <el-button size="small" :icon="ZoomOut" :disabled="graphZoom <= 0.6" @click="changeZoom(-0.1)" />
            <el-button size="small" class="zoom-value" @click="resetZoom">{{ Math.round(graphZoom * 100) }}%</el-button>
            <el-button size="small" :icon="ZoomIn" :disabled="graphZoom >= 1.6" @click="changeZoom(0.1)" />
          </el-button-group>
        </div>
      </div>

      <div v-loading="loading" class="flow-canvas" @wheel.ctrl.prevent="handleGraphWheel">
        <el-empty v-if="!loading && !edges.length" description="暂无运行血缘；SQL 调度任务成功回调后会自动生成" />
        <div v-if="edges.length" class="flow-content" :style="{ zoom: graphZoom }">
          <template v-for="(stage, stageIndex) in nodeStages" :key="stageIndex">
            <section class="flow-stage">
              <div class="stage-title"><span>{{ stageLabel(stageIndex) }}</span><small>{{ stage.length }} 个表</small></div>
              <button v-for="node in stage" :key="node.id" type="button" class="asset-node" :class="[nodeRole(node), nodeFocusClass(node), { active: selectedNode?.id === node.id }]" @click="selectNode(node)">
                <span class="node-icon"><el-icon><Coin /></el-icon></span>
                <span class="node-content"><strong>{{ node.name }}</strong><small>{{ node.schema }}</small><span class="node-meta"><em>{{ node.inCount }} 上游</em><em>{{ node.outCount }} 下游</em></span></span>
              </button>
            </section>
            <div v-if="stageIndex < nodeStages.length - 1" class="stage-arrow" :class="{ dimmed: selectedNode && !stage.some(node => focusedNodeIds.has(node.id)) }"><span></span><el-icon><ArrowRight /></el-icon></div>
          </template>
        </div>
      </div>

      <el-card v-if="selectedNode" shadow="never" class="selected-detail">
        <template #header>
          <div class="detail-title"><div><span>表节点详情</span><strong>{{ selectedNode.name }}</strong><code>{{ selectedNode.fqn }}</code></div><el-tag effect="plain">{{ selectedNode.schema }}</el-tag></div>
        </template>
        <div class="relation-grid">
          <section class="relation-section">
            <div class="relation-title"><span class="relation-dot source"></span><strong>上游输入</strong><small>{{ selectedRelations.upstream.length }} 条关系</small></div>
            <div v-if="selectedRelations.upstream.length" class="relation-list">
              <button v-for="edge in selectedRelations.upstream" :key="edge.id" type="button" class="relation-card" :class="{ active: selectedEdge?.id === edge.id }" @click="selectedEdge = edge">
                <span class="relation-direction"><strong>{{ edge.source_name }}</strong><small>{{ edge.source_fqn }}</small></span><el-icon><ArrowRight /></el-icon><span class="relation-metrics"><em>{{ edge.success_count || 0 }} 次成功</em><small>{{ formatTime(edge.last_seen_at) }}</small></span>
              </button>
            </div>
            <el-empty v-else description="无上游表" :image-size="44" />
          </section>
          <section class="relation-section">
            <div class="relation-title"><span class="relation-dot target"></span><strong>下游输出</strong><small>{{ selectedRelations.downstream.length }} 条关系</small></div>
            <div v-if="selectedRelations.downstream.length" class="relation-list">
              <button v-for="edge in selectedRelations.downstream" :key="edge.id" type="button" class="relation-card" :class="{ active: selectedEdge?.id === edge.id }" @click="selectedEdge = edge">
                <span class="relation-direction"><strong>{{ edge.target_name }}</strong><small>{{ edge.target_fqn }}</small></span><el-icon><ArrowRight /></el-icon><span class="relation-metrics"><em>{{ edge.success_count || 0 }} 次成功</em><small>{{ formatTime(edge.last_seen_at) }}</small></span>
              </button>
            </div>
            <el-empty v-else description="无下游表" :image-size="44" />
          </section>
        </div>

        <el-collapse-transition>
          <div v-if="selectedEdge" class="edge-detail">
            <div class="edge-flow"><strong>{{ selectedEdge.source_name }}</strong><el-icon><ArrowRight /></el-icon><strong>{{ selectedEdge.target_name }}</strong></div>
            <div class="edge-meta">
              <div><span>最近任务</span><strong>{{ selectedEdge.last_task_id || "-" }}</strong></div><div><span>DAG Run</span><strong>{{ selectedEdge.last_dag_run_id || "-" }}</strong></div><div><span>成功次数</span><strong>{{ selectedEdge.success_count || 0 }}</strong></div><div><span>最近产生</span><strong>{{ formatTime(selectedEdge.last_seen_at) }}</strong></div>
            </div>
          </div>
        </el-collapse-transition>
      </el-card>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { ArrowRight, Coin, Refresh, Search, ZoomIn, ZoomOut } from "@element-plus/icons-vue";
import { dataAssetApi } from "@/api";

interface LineageEdge { id:number; source_asset_id?:number; target_asset_id?:number; source_name:string; source_fqn:string; target_name:string; target_fqn:string; lineage_type:string; last_task_id?:string; last_dag_run_id?:string; last_seen_at?:string; success_count?:number }
interface GraphNode { id:string; name:string; fqn:string; schema:string; depth:number; inCount:number; outCount:number }

const loading = ref(false), keyword = ref("");
const edges = ref<LineageEdge[]>([]), total = ref(0);
const selectedNode = ref<GraphNode>(), selectedEdge = ref<LineageEdge>();
const graphZoom = ref(1);
function assetKey(id:number|undefined,fqn:string){ return id ? `asset-${id}` : `fqn-${fqn}`; }
function schemaName(fqn:string){ const parts=fqn.split("."); return parts.length>1 ? parts[parts.length-2] : "物理表"; }

const graphData = computed(() => {
  const nodes=new Map<string,GraphNode>(), adjacency=new Map<string,Set<string>>(), reverseAdjacency=new Map<string,Set<string>>(), indegree=new Map<string,number>();
  const ensureNode=(id:string,name:string,fqn:string)=>{ if(!nodes.has(id)){ nodes.set(id,{id,name,fqn,schema:schemaName(fqn),depth:0,inCount:0,outCount:0}); adjacency.set(id,new Set()); indegree.set(id,0); } };
  edges.value.forEach(edge=>{ const source=assetKey(edge.source_asset_id,edge.source_fqn), target=assetKey(edge.target_asset_id,edge.target_fqn); ensureNode(source,edge.source_name,edge.source_fqn); ensureNode(target,edge.target_name,edge.target_fqn); if(!adjacency.get(source)?.has(target)){ adjacency.get(source)?.add(target); if(!reverseAdjacency.has(target))reverseAdjacency.set(target,new Set()); reverseAdjacency.get(target)!.add(source); indegree.set(target,(indegree.get(target)||0)+1); nodes.get(source)!.outCount++; nodes.get(target)!.inCount++; } });
  const remaining=new Map(indegree), queue=[...nodes.keys()].filter(id=>remaining.get(id)===0); let cursor=0;
  while(cursor<queue.length){ const source=queue[cursor++]; adjacency.get(source)?.forEach(target=>{ nodes.get(target)!.depth=Math.max(nodes.get(target)!.depth,nodes.get(source)!.depth+1); remaining.set(target,(remaining.get(target)||0)-1); if(remaining.get(target)===0) queue.push(target); }); }
  const maxDepth=Math.max(0,...[...nodes.values()].map(node=>node.depth)); nodes.forEach(node=>{ if((remaining.get(node.id)||0)>0) node.depth=maxDepth+1; });
  const stages:GraphNode[][]=[]; nodes.forEach(node=>{ if(!stages[node.depth]) stages[node.depth]=[]; stages[node.depth].push(node); }); stages.forEach(stage=>stage.sort((a,b)=>a.schema.localeCompare(b.schema)||a.name.localeCompare(b.name)));
  return {nodes,adjacency,reverseAdjacency,stages:stages.filter(Boolean)};
});
const nodeStages=computed(()=>graphData.value.stages), nodeCount=computed(()=>graphData.value.nodes.size);
const lineageStats=computed(()=>{ const nodes=[...graphData.value.nodes.values()], tasks=new Set(edges.value.map(edge=>edge.last_task_id).filter(Boolean)), latest=edges.value.map(edge=>edge.last_seen_at).filter((value):value is string=>!!value).sort().at(-1); return {sources:nodes.filter(node=>node.inCount===0).length,targets:nodes.filter(node=>node.outCount===0).length,intermediates:nodes.filter(node=>node.inCount>0&&node.outCount>0).length,tasks:tasks.size,latest}; });
const selectedRelations=computed(()=>{ if(!selectedNode.value) return {upstream:[] as LineageEdge[],downstream:[] as LineageEdge[]}; return {upstream:edges.value.filter(edge=>assetKey(edge.target_asset_id,edge.target_fqn)===selectedNode.value!.id),downstream:edges.value.filter(edge=>assetKey(edge.source_asset_id,edge.source_fqn)===selectedNode.value!.id)}; });
const focusedNodeIds=computed(()=>{ const focused=new Set<string>(); if(!selectedNode.value)return focused; const visit=(start:string,map:Map<string,Set<string>>)=>{ const queue=[start]; while(queue.length){ const current=queue.shift()!; if(focused.has(current)&&current!==start)continue; focused.add(current); (map.get(current)||[]).forEach(next=>{ if(!focused.has(next))queue.push(next); }); } }; visit(selectedNode.value.id,graphData.value.adjacency); visit(selectedNode.value.id,graphData.value.reverseAdjacency); return focused; });

function nodeRole(node:GraphNode){ if(node.inCount===0)return "source"; if(node.outCount===0)return "target"; return "middle"; }
function stageLabel(index:number){ if(nodeStages.value.length===1)return "数据表"; if(index===0)return "上游源表"; if(index===nodeStages.value.length-1)return "下游目标表"; return `处理层 ${index}`; }
function selectNode(node:GraphNode){ if(selectedNode.value?.id===node.id){ clearFocus(); return; } selectedNode.value=node; selectedEdge.value=undefined; }
function clearFocus(){ selectedNode.value=undefined; selectedEdge.value=undefined; }
function nodeFocusClass(node:GraphNode){ return selectedNode.value ? { related:focusedNodeIds.value.has(node.id), dimmed:!focusedNodeIds.value.has(node.id) } : {}; }
function changeZoom(delta:number){ graphZoom.value=Math.min(1.6,Math.max(0.6,Math.round((graphZoom.value+delta)*10)/10)); }
function resetZoom(){ graphZoom.value=1; }
function handleGraphWheel(event:WheelEvent){ changeZoom(event.deltaY<0?0.1:-0.1); }
function formatTime(value?:string){ return value?new Date(value).toLocaleString("zh-CN",{hour12:false}):"-"; }
function formatShortTime(value?:string){ return value?new Date(value).toLocaleString("zh-CN",{month:"2-digit",day:"2-digit",hour:"2-digit",minute:"2-digit",hour12:false}):"-"; }
async function loadLineage(){ loading.value=true; clearFocus(); try{ const result:any=await dataAssetApi.lineage(keyword.value); edges.value=result.edges||[]; total.value=result.total||0; }finally{ loading.value=false; } }
function resetView(){ keyword.value=""; resetZoom(); void loadLineage(); }
onMounted(loadLineage);
</script>

<style scoped lang="scss">
.lineage-page{padding:16px}.header{display:flex;align-items:center;justify-content:space-between;gap:16px}.title{font-size:18px;font-weight:600}.subtitle{margin-top:5px;color:var(--el-text-color-secondary);font-size:12px}.toolbar{display:flex;align-items:center;gap:10px;margin-bottom:14px}.toolbar .el-input{width:min(520px,45vw)}
.lineage-overview{display:grid;grid-template-columns:minmax(230px,1.6fr) repeat(6,minmax(82px,.55fr));gap:10px;padding:14px;border:1px solid var(--el-border-color-lighter);border-radius:10px;background:linear-gradient(135deg,#f8fafc,#f1f5f9)}.overview-identity{display:flex;min-width:0;flex-direction:column;gap:4px;padding-right:12px;border-right:1px solid var(--el-border-color-lighter)}.overview-identity strong{font-size:15px}.overview-identity>span:last-child{color:var(--el-text-color-secondary);font-size:11px}.overview-label,.overview-stat span{color:var(--el-text-color-secondary);font-size:11px}.overview-stat{display:flex;flex-direction:column;align-items:center;justify-content:center;gap:7px}.overview-stat strong{font-size:17px}.overview-stat.source strong{color:#2563eb}.overview-stat.middle strong{color:#7c3aed}.overview-stat.target strong{color:#059669}.overview-stat .latest-time{font-size:12px;white-space:nowrap}
.flow-heading{display:flex;align-items:center;justify-content:space-between;gap:16px;margin:22px 0 12px}.flow-heading>div:first-child{display:flex;align-items:baseline;gap:10px}.flow-heading span{color:var(--el-text-color-secondary);font-size:12px}.flow-actions{display:flex;align-items:center;gap:10px}.flow-legend{display:flex;align-items:center;gap:6px;color:var(--el-text-color-secondary);font-size:11px}.flow-legend i{width:8px;height:8px;margin-left:5px;border-radius:50%}.flow-legend i.source{background:#2563eb}.flow-legend i.middle{background:#7c3aed}.flow-legend i.target{background:#059669}.zoom-value{min-width:58px}
.flow-canvas{min-height:360px;max-height:620px;padding:20px;overflow:auto;border:1px solid #dbe4ef;border-radius:10px;background-color:#f8fafc;background-image:radial-gradient(#cbd5e1 1px,transparent 1px);background-size:18px 18px}.flow-canvas>.el-empty{width:100%}.flow-content{display:flex;align-items:center;min-width:max-content;min-height:320px;transform-origin:left center;transition:zoom .15s ease}.flow-stage{display:flex;min-width:220px;flex-direction:column;align-self:stretch;justify-content:center;gap:10px}.stage-title{display:flex;align-items:center;justify-content:space-between;padding:0 4px;color:#475569;font-size:12px}.stage-title small{color:#94a3b8}.stage-arrow{display:flex;flex:0 0 72px;align-items:center;color:#94a3b8;transition:opacity .2s ease}.stage-arrow.dimmed{opacity:.18}.stage-arrow span{height:2px;flex:1;background:#cbd5e1}.stage-arrow .el-icon{margin-left:-2px;font-size:18px}
.asset-node{display:flex;width:220px;align-items:flex-start;gap:10px;padding:12px;border:1px solid #dbe4ef;border-left:4px solid #2563eb;border-radius:8px;background:#fff;color:inherit;text-align:left;cursor:pointer;box-shadow:0 2px 6px rgba(15,23,42,.05);transition:opacity .22s ease,filter .22s ease,transform .18s ease,box-shadow .18s ease}.asset-node.middle{border-left-color:#7c3aed}.asset-node.target{border-left-color:#059669}.asset-node:hover,.asset-node.active{border-color:var(--el-color-primary-light-5);border-left-color:var(--el-color-primary);box-shadow:0 5px 16px rgba(37,99,235,.14);transform:translateY(-1px)}.asset-node.related{opacity:1;filter:none}.asset-node.dimmed{opacity:.18;filter:grayscale(.75)}.asset-node.dimmed:hover{opacity:.55}.node-icon{display:grid;flex:0 0 30px;height:30px;place-items:center;border-radius:50%;background:#eff6ff;color:#2563eb;font-size:17px}.asset-node.middle .node-icon{background:#f5f3ff;color:#7c3aed}.asset-node.target .node-icon{background:#ecfdf5;color:#059669}.node-content{display:flex;min-width:0;flex:1;flex-direction:column;gap:4px}.node-content strong,.node-content small{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.node-content strong{font-size:13px}.node-content small{color:var(--el-text-color-secondary);font-size:10px}.node-meta{display:flex;justify-content:space-between;gap:8px;margin-top:3px;color:#64748b;font-size:10px}.node-meta em{font-style:normal}
.selected-detail{margin-top:16px}.detail-title{display:flex;align-items:center;justify-content:space-between;gap:16px}.detail-title>div{display:flex;min-width:0;align-items:center;gap:12px}.detail-title span{color:var(--el-text-color-secondary);font-size:12px}.detail-title code{overflow:hidden;color:#64748b;font-size:11px;text-overflow:ellipsis;white-space:nowrap}.relation-grid{display:grid;grid-template-columns:1fr 1fr;gap:16px}.relation-section{min-width:0;padding:14px;border:1px solid var(--el-border-color-lighter);border-radius:8px;background:#fafcff}.relation-title{display:flex;align-items:center;gap:8px;margin-bottom:10px}.relation-title small{margin-left:auto;color:var(--el-text-color-secondary)}.relation-dot{width:9px;height:9px;border-radius:50%}.relation-dot.source{background:#2563eb}.relation-dot.target{background:#059669}.relation-list{display:grid;gap:8px;max-height:240px;overflow:auto}.relation-card{display:grid;grid-template-columns:minmax(0,1fr) 24px auto;align-items:center;gap:8px;width:100%;padding:10px;border:1px solid #e2e8f0;border-radius:7px;background:#fff;color:inherit;text-align:left;cursor:pointer}.relation-card:hover,.relation-card.active{border-color:var(--el-color-primary-light-5);background:#f8fbff}.relation-direction,.relation-metrics{display:flex;min-width:0;flex-direction:column;gap:3px}.relation-direction strong,.relation-direction small{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.relation-direction small,.relation-metrics small{color:var(--el-text-color-secondary);font-size:10px}.relation-metrics{align-items:flex-end}.relation-metrics em{color:#475569;font-size:11px;font-style:normal;white-space:nowrap}.relation-card>.el-icon{color:#94a3b8}
.edge-detail{margin-top:14px;padding:14px;border:1px dashed #cbd5e1;border-radius:8px;background:#f8fafc}.edge-flow{display:flex;align-items:center;justify-content:center;gap:14px;color:#334155}.edge-flow .el-icon{color:var(--el-color-primary)}.edge-meta{display:grid;grid-template-columns:1fr 1.5fr .6fr 1fr;gap:18px;margin-top:14px;padding-top:14px;border-top:1px dashed var(--el-border-color)}.edge-meta>div{display:flex;min-width:0;flex-direction:column;gap:4px}.edge-meta span{color:var(--el-text-color-secondary);font-size:11px}.edge-meta strong{overflow:hidden;font-size:12px;text-overflow:ellipsis;white-space:nowrap}
@media(max-width:1000px){.lineage-overview{grid-template-columns:repeat(3,1fr)}.overview-identity{grid-column:1/-1;border-right:0;border-bottom:1px solid var(--el-border-color-lighter);padding-bottom:10px}.flow-heading{align-items:flex-start;flex-direction:column}.flow-actions{width:100%;flex-wrap:wrap}.relation-grid{grid-template-columns:1fr}.edge-meta{grid-template-columns:1fr 1fr}}@media(max-width:700px){.toolbar{flex-wrap:wrap}.toolbar .el-input{width:100%}.lineage-overview{grid-template-columns:1fr 1fr}.flow-legend{width:100%}.detail-title>div{align-items:flex-start;flex-direction:column;gap:4px}}
</style>
