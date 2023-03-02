import{h as A,j as u,t as n,v as U,z as I,X as yt,Q as ke,r as E,w as j,af as Ne,o as Qe,ab as _t,a2 as qt,m as He,C as Le,G as Pe,ag as ze,ah as Ue,aq as z,g as Me,Z as wt,Y as je,ar as Ce,as as De,at as Ct,k as Ke,au as kt,a9 as G,S as ie,_ as Pt,H as xt,I as Rt,a6 as Tt}from"./index.422cc3a0.js";import{a as se,d as ce,j as Bt,p as Vt}from"./api.8025d512.js";import{Q as pt}from"./QList.7f24c43e.js";import{u as Ot,c as $t,d as Ft,e as Lt,f as We,g as Mt,Q as jt}from"./QPage.6206ab40.js";var kl=A({name:"QTd",props:{props:Object,autoWidth:Boolean,noHover:Boolean},setup(e,{slots:a}){const l=I(),c=u(()=>"q-td"+(e.autoWidth===!0?" q-table--col-auto-width":"")+(e.noHover===!0?" q-td--no-hover":"")+" ");return()=>{if(e.props===void 0)return n("td",{class:c.value},U(a.default));const r=l.vnode.key,v=(e.props.colsMap!==void 0?e.props.colsMap[r]:null)||e.props.col;if(v===void 0)return;const{row:i}=e.props;return n("td",{class:c.value+v.__tdClass(i),style:v.__tdStyle(i)},U(a.default))}}}),Dt=A({name:"QTh",props:{props:Object,autoWidth:Boolean},emits:["click"],setup(e,{slots:a,emit:l}){const c=I(),{proxy:{$q:r}}=c,v=i=>{l("click",i)};return()=>{if(e.props===void 0)return n("th",{class:e.autoWidth===!0?"q-table--col-auto-width":"",onClick:v},U(a.default));let i,d;const f=c.vnode.key;if(f){if(i=e.props.colsMap[f],i===void 0)return}else i=e.props.col;if(i.sortable===!0){const o=i.align==="right"?"unshift":"push";d=yt(a.default,[]),d[o](n(ke,{class:i.__iconClass,name:r.iconSet.table.arrowUp}))}else d=U(a.default);const m={class:i.__thClass+(e.autoWidth===!0?" q-table--col-auto-width":""),style:i.headerStyle,onClick:o=>{i.sortable===!0&&e.props.sort(i),v(o)}};return n("th",m,d)}}});const Et=["horizontal","vertical","cell","none"];var At=A({name:"QMarkupTable",props:{...se,dense:Boolean,flat:Boolean,bordered:Boolean,square:Boolean,wrapCells:Boolean,separator:{type:String,default:"horizontal",validator:e=>Et.includes(e)}},setup(e,{slots:a}){const l=I(),c=ce(e,l.proxy.$q),r=u(()=>`q-markup-table q-table__container q-table__card q-table--${e.separator}-separator`+(c.value===!0?" q-table--dark q-table__card--dark q-dark":"")+(e.dense===!0?" q-table--dense":"")+(e.flat===!0?" q-table--flat":"")+(e.bordered===!0?" q-table--bordered":"")+(e.square===!0?" q-table--square":"")+(e.wrapCells===!1?" q-table--no-wrap":""));return()=>n("div",{class:r.value},[n("table",{class:"q-table"},U(a.default))])}});function Ge(e,a){return n("div",e,[n("table",{class:"q-table"},a)])}const It={list:pt,table:At},Nt=["list","table","__qtable"];var Qt=A({name:"QVirtualScroll",props:{...Ot,type:{type:String,default:"list",validator:e=>Nt.includes(e)},items:{type:Array,default:()=>[]},itemsFn:Function,itemsSize:Number,scrollTarget:{default:void 0}},setup(e,{slots:a,attrs:l}){let c;const r=E(null),v=u(()=>e.itemsSize>=0&&e.itemsFn!==void 0?parseInt(e.itemsSize,10):Array.isArray(e.items)?e.items.length:0),{virtualScrollSliceRange:i,localResetVirtualScroll:d,padVirtualScroll:f,onVirtualScrollEvt:m}=$t({virtualScrollLength:v,getVirtualScrollTarget:w,getVirtualScrollEl:k}),o=u(()=>{if(v.value===0)return[];const V=(O,x)=>({index:i.value.from+x,item:O});return e.itemsFn===void 0?e.items.slice(i.value.from,i.value.to).map(V):e.itemsFn(i.value.from,i.value.to-i.value.from).map(V)}),b=u(()=>"q-virtual-scroll q-virtual-scroll"+(e.virtualScrollHorizontal===!0?"--horizontal":"--vertical")+(e.scrollTarget!==void 0?"":" scroll")),q=u(()=>e.scrollTarget!==void 0?{}:{tabindex:0});j(v,()=>{d()}),j(()=>e.scrollTarget,()=>{S(),y()});function k(){return r.value.$el||r.value}function w(){return c}function y(){c=Bt(k(),e.scrollTarget),c.addEventListener("scroll",m,Le.passive)}function S(){c!==void 0&&(c.removeEventListener("scroll",m,Le.passive),c=void 0)}function B(){let V=f(e.type==="list"?"div":"tbody",o.value.map(a.default));return a.before!==void 0&&(V=a.before().concat(V)),Pe(a.after,V)}return Ne(()=>{d()}),Qe(()=>{y()}),_t(()=>{y()}),qt(()=>{S()}),He(()=>{S()}),()=>{if(a.default===void 0){console.error("QVirtualScroll: default scoped slot is required for rendering");return}return e.type==="__qtable"?Ge({ref:r,class:"q-table__middle "+b.value},B()):n(It[e.type],{...l,ref:r,class:[l.class,b.value],...q.value},B)}}});const Ht={xs:2,sm:4,md:6,lg:10,xl:14};function Ee(e,a,l){return{transform:a===!0?`translateX(${l.lang.rtl===!0?"-":""}100%) scale3d(${-e},1,1)`:`scale3d(${e},1,1)`}}var zt=A({name:"QLinearProgress",props:{...se,...ze,value:{type:Number,default:0},buffer:Number,color:String,trackColor:String,reverse:Boolean,stripe:Boolean,indeterminate:Boolean,query:Boolean,rounded:Boolean,animationSpeed:{type:[String,Number],default:2100},instantFeedback:Boolean},setup(e,{slots:a}){const{proxy:l}=I(),c=ce(e,l.$q),r=Ue(e,Ht),v=u(()=>e.indeterminate===!0||e.query===!0),i=u(()=>e.reverse!==e.query),d=u(()=>({...r.value!==null?r.value:{},"--q-linear-progress-speed":`${e.animationSpeed}ms`})),f=u(()=>"q-linear-progress"+(e.color!==void 0?` text-${e.color}`:"")+(e.reverse===!0||e.query===!0?" q-linear-progress--reverse":"")+(e.rounded===!0?" rounded-borders":"")),m=u(()=>Ee(e.buffer!==void 0?e.buffer:1,i.value,l.$q)),o=u(()=>`with${e.instantFeedback===!0?"out":""}-transition`),b=u(()=>`q-linear-progress__track absolute-full q-linear-progress__track--${o.value} q-linear-progress__track--${c.value===!0?"dark":"light"}`+(e.trackColor!==void 0?` bg-${e.trackColor}`:"")),q=u(()=>Ee(v.value===!0?1:e.value,i.value,l.$q)),k=u(()=>`q-linear-progress__model absolute-full q-linear-progress__model--${o.value} q-linear-progress__model--${v.value===!0?"in":""}determinate`),w=u(()=>({width:`${e.value*100}%`})),y=u(()=>`q-linear-progress__stripe absolute-${e.reverse===!0?"right":"left"} q-linear-progress__stripe--${o.value}`);return()=>{const S=[n("div",{class:b.value,style:m.value}),n("div",{class:k.value,style:q.value})];return e.stripe===!0&&v.value===!1&&S.push(n("div",{class:y.value,style:w.value})),n("div",{class:f.value,style:d.value,role:"progressbar","aria-valuemin":0,"aria-valuemax":1,"aria-valuenow":e.indeterminate===!0?void 0:e.value},Pe(a.default,S))}}});function Ut(e,a){const l=E(null),c=u(()=>e.disable===!0?null:n("span",{ref:l,class:"no-outline",tabindex:-1}));function r(v){const i=a.value;v!==void 0&&v.type.indexOf("key")===0?i!==null&&document.activeElement!==i&&i.contains(document.activeElement)===!0&&i.focus():l.value!==null&&(v===void 0||i!==null&&i.contains(v.target)===!0)&&l.value.focus()}return{refocusTargetEl:c,refocusTarget:r}}var Kt={xs:30,sm:35,md:40,lg:50,xl:60};const Wt={...se,...ze,...Ft,modelValue:{required:!0,default:null},val:{},trueValue:{default:!0},falseValue:{default:!1},indeterminateValue:{default:null},checkedIcon:String,uncheckedIcon:String,indeterminateIcon:String,toggleOrder:{type:String,validator:e=>e==="tf"||e==="ft"},toggleIndeterminate:Boolean,label:String,leftLabel:Boolean,color:String,keepColor:Boolean,dense:Boolean,disable:Boolean,tabindex:[String,Number]},Gt=["update:modelValue"];function Xt(e,a){const{props:l,slots:c,emit:r,proxy:v}=I(),{$q:i}=v,d=ce(l,i),f=E(null),{refocusTargetEl:m,refocusTarget:o}=Ut(l,f),b=Ue(l,Kt),q=u(()=>l.val!==void 0&&Array.isArray(l.modelValue)),k=u(()=>{const C=z(l.val);return q.value===!0?l.modelValue.findIndex(F=>z(F)===C):-1}),w=u(()=>q.value===!0?k.value>-1:z(l.modelValue)===z(l.trueValue)),y=u(()=>q.value===!0?k.value===-1:z(l.modelValue)===z(l.falseValue)),S=u(()=>w.value===!1&&y.value===!1),B=u(()=>l.disable===!0?-1:l.tabindex||0),V=u(()=>`q-${e} cursor-pointer no-outline row inline no-wrap items-center`+(l.disable===!0?" disabled":"")+(d.value===!0?` q-${e}--dark`:"")+(l.dense===!0?` q-${e}--dense`:"")+(l.leftLabel===!0?" reverse":"")),O=u(()=>{const C=w.value===!0?"truthy":y.value===!0?"falsy":"indet",F=l.color!==void 0&&(l.keepColor===!0||(e==="toggle"?w.value===!0:y.value!==!0))?` text-${l.color}`:"";return`q-${e}__inner relative-position non-selectable q-${e}__inner--${C}${F}`}),x=u(()=>{const C={type:"checkbox"};return l.name!==void 0&&Object.assign(C,{".checked":w.value,"^checked":w.value===!0?"checked":void 0,name:l.name,value:q.value===!0?l.val:l.trueValue}),C}),T=Lt(x),N=u(()=>{const C={tabindex:B.value,role:e==="toggle"?"switch":"checkbox","aria-label":l.label,"aria-checked":S.value===!0?"mixed":w.value===!0?"true":"false"};return l.disable===!0&&(C["aria-disabled"]="true"),C});function K(C){C!==void 0&&(Me(C),o(C)),l.disable!==!0&&r("update:modelValue",W(),C)}function W(){if(q.value===!0){if(w.value===!0){const C=l.modelValue.slice();return C.splice(k.value,1),C}return l.modelValue.concat([l.val])}if(w.value===!0){if(l.toggleOrder!=="ft"||l.toggleIndeterminate===!1)return l.falseValue}else if(y.value===!0){if(l.toggleOrder==="ft"||l.toggleIndeterminate===!1)return l.trueValue}else return l.toggleOrder!=="ft"?l.trueValue:l.falseValue;return l.indeterminateValue}function Y(C){(C.keyCode===13||C.keyCode===32)&&Me(C)}function $(C){(C.keyCode===13||C.keyCode===32)&&K(C)}const D=a(w,S);return Object.assign(v,{toggle:K}),()=>{const C=D();l.disable!==!0&&T(C,"unshift",` q-${e}__native absolute q-ma-none q-pa-none`);const F=[n("div",{class:O.value,style:b.value,"aria-hidden":"true"},C)];m.value!==null&&F.push(m.value);const Z=l.label!==void 0?Pe(c.default,[l.label]):U(c.default);return Z!==void 0&&F.push(n("div",{class:`q-${e}__label q-anchor--skip`},Z)),n("div",{ref:f,class:V.value,...N.value,onClick:K,onKeydown:Y,onKeyup:$},F)}}const Yt=n("div",{key:"svg",class:"q-checkbox__bg absolute"},[n("svg",{class:"q-checkbox__svg fit absolute-full",viewBox:"0 0 24 24"},[n("path",{class:"q-checkbox__truthy",fill:"none",d:"M1.73,12.91 8.1,19.28 22.79,4.59"}),n("path",{class:"q-checkbox__indet",d:"M4,14H20V10H4"})])]);var we=A({name:"QCheckbox",props:Wt,emits:Gt,setup(e){function a(l,c){const r=u(()=>(l.value===!0?e.checkedIcon:c.value===!0?e.indeterminateIcon:e.uncheckedIcon)||null);return()=>r.value!==null?[n("div",{key:"icon",class:"q-checkbox__icon-container absolute-full flex flex-center no-wrap"},[n(ke,{class:"q-checkbox__icon",name:r.value})])]:[Yt]}return Xt("checkbox",a)}});let X=0;const Zt={fullscreen:Boolean,noRouteFullscreenExit:Boolean},Jt=["update:fullscreen","fullscreen"];function el(){const e=I(),{props:a,emit:l,proxy:c}=e;let r,v,i;const d=E(!1);wt(e)===!0&&j(()=>c.$route.fullPath,()=>{a.noRouteFullscreenExit!==!0&&o()}),j(()=>a.fullscreen,b=>{d.value!==b&&f()}),j(d,b=>{l("update:fullscreen",b),l("fullscreen",b)});function f(){d.value===!0?o():m()}function m(){d.value!==!0&&(d.value=!0,i=c.$el.parentNode,i.replaceChild(v,c.$el),document.body.appendChild(c.$el),X++,X===1&&document.body.classList.add("q-body--fullscreen-mixin"),r={handler:o},je.add(r))}function o(){d.value===!0&&(r!==void 0&&(je.remove(r),r=void 0),i.replaceChild(c.$el,v),d.value=!1,X=Math.max(0,X-1),X===0&&(document.body.classList.remove("q-body--fullscreen-mixin"),c.$el.scrollIntoView!==void 0&&setTimeout(()=>{c.$el.scrollIntoView()})))}return Ne(()=>{v=document.createElement("span")}),Qe(()=>{a.fullscreen===!0&&m()}),He(o),Object.assign(c,{toggleFullscreen:f,setFullscreen:m,exitFullscreen:o}),{inFullscreen:d,toggleFullscreen:f}}function tl(e,a){return new Date(e)-new Date(a)}const ll={sortMethod:Function,binaryStateSort:Boolean,columnSortOrder:{type:String,validator:e=>e==="ad"||e==="da",default:"ad"}};function al(e,a,l,c){const r=u(()=>{const{sortBy:d}=a.value;return d&&l.value.find(f=>f.name===d)||null}),v=u(()=>e.sortMethod!==void 0?e.sortMethod:(d,f,m)=>{const o=l.value.find(k=>k.name===f);if(o===void 0||o.field===void 0)return d;const b=m===!0?-1:1,q=typeof o.field=="function"?k=>o.field(k):k=>k[o.field];return d.sort((k,w)=>{let y=q(k),S=q(w);return y==null?-1*b:S==null?1*b:o.sort!==void 0?o.sort(y,S,k,w)*b:Ce(y)===!0&&Ce(S)===!0?(y-S)*b:De(y)===!0&&De(S)===!0?tl(y,S)*b:typeof y=="boolean"&&typeof S=="boolean"?(y-S)*b:([y,S]=[y,S].map(B=>(B+"").toLocaleString().toLowerCase()),y<S?-1*b:y===S?0:b)})});function i(d){let f=e.columnSortOrder;if(Ct(d)===!0)d.sortOrder&&(f=d.sortOrder),d=d.name;else{const b=l.value.find(q=>q.name===d);b!==void 0&&b.sortOrder&&(f=b.sortOrder)}let{sortBy:m,descending:o}=a.value;m!==d?(m=d,o=f==="da"):e.binaryStateSort===!0?o=!o:o===!0?f==="ad"?m=null:o=!1:f==="ad"?o=!0:m=null,c({sortBy:m,descending:o,page:1})}return{columnToSort:r,computedSortMethod:v,sort:i}}const nl={filter:[String,Object],filterMethod:Function};function rl(e,a){const l=u(()=>e.filterMethod!==void 0?e.filterMethod:(c,r,v,i)=>{const d=r?r.toLowerCase():"";return c.filter(f=>v.some(m=>{const o=i(m,f)+"";return(o==="undefined"||o==="null"?"":o.toLowerCase()).indexOf(d)!==-1}))});return j(()=>e.filter,()=>{Ke(()=>{a({page:1},!0)})},{deep:!0}),{computedFilterMethod:l}}function ol(e,a){for(const l in a)if(a[l]!==e[l])return!1;return!0}function Ae(e){return e.page<1&&(e.page=1),e.rowsPerPage!==void 0&&e.rowsPerPage<1&&(e.rowsPerPage=0),e}const il={pagination:Object,rowsPerPageOptions:{type:Array,default:()=>[5,7,10,15,20,25,50,0]},"onUpdate:pagination":[Function,Array]};function ul(e,a){const{props:l,emit:c}=e,r=E(Object.assign({sortBy:null,descending:!1,page:1,rowsPerPage:l.rowsPerPageOptions.length>0?l.rowsPerPageOptions[0]:5},l.pagination)),v=u(()=>{const o=l["onUpdate:pagination"]!==void 0?{...r.value,...l.pagination}:r.value;return Ae(o)}),i=u(()=>v.value.rowsNumber!==void 0);function d(o){f({pagination:o,filter:l.filter})}function f(o={}){Ke(()=>{c("request",{pagination:o.pagination||v.value,filter:o.filter||l.filter,getCellValue:a})})}function m(o,b){const q=Ae({...v.value,...o});if(ol(v.value,q)===!0){i.value===!0&&b===!0&&d(q);return}if(i.value===!0){d(q);return}l.pagination!==void 0&&l["onUpdate:pagination"]!==void 0?c("update:pagination",q):r.value=q}return{innerPagination:r,computedPagination:v,isServerSide:i,requestServerInteraction:f,setPagination:m}}function sl(e,a,l,c,r,v){const{props:i,emit:d,proxy:{$q:f}}=e,m=u(()=>c.value===!0?l.value.rowsNumber||0:v.value),o=u(()=>{const{page:x,rowsPerPage:T}=l.value;return(x-1)*T}),b=u(()=>{const{page:x,rowsPerPage:T}=l.value;return x*T}),q=u(()=>l.value.page===1),k=u(()=>l.value.rowsPerPage===0?1:Math.max(1,Math.ceil(m.value/l.value.rowsPerPage))),w=u(()=>b.value===0?!0:l.value.page>=k.value),y=u(()=>(i.rowsPerPageOptions.includes(a.value.rowsPerPage)?i.rowsPerPageOptions:[a.value.rowsPerPage].concat(i.rowsPerPageOptions)).map(T=>({label:T===0?f.lang.table.allRows:""+T,value:T})));j(k,(x,T)=>{if(x===T)return;const N=l.value.page;x&&!N?r({page:1}):x<N&&r({page:x})});function S(){r({page:1})}function B(){const{page:x}=l.value;x>1&&r({page:x-1})}function V(){const{page:x,rowsPerPage:T}=l.value;b.value>0&&x*T<m.value&&r({page:x+1})}function O(){r({page:k.value})}return i["onUpdate:pagination"]!==void 0&&d("update:pagination",{...l.value}),{firstRowIndex:o,lastRowIndex:b,isFirstPage:q,isLastPage:w,pagesNumber:k,computedRowsPerPageOptions:y,computedRowsNumber:m,firstPage:S,prevPage:B,nextPage:V,lastPage:O}}const cl={selection:{type:String,default:"none",validator:e=>["single","multiple","none"].includes(e)},selected:{type:Array,default:()=>[]}},dl=["update:selected","selection"];function vl(e,a,l,c){const r=u(()=>{const w={};return e.selected.map(c.value).forEach(y=>{w[y]=!0}),w}),v=u(()=>e.selection!=="none"),i=u(()=>e.selection==="single"),d=u(()=>e.selection==="multiple"),f=u(()=>l.value.length>0&&l.value.every(w=>r.value[c.value(w)]===!0)),m=u(()=>f.value!==!0&&l.value.some(w=>r.value[c.value(w)]===!0)),o=u(()=>e.selected.length);function b(w){return r.value[w]===!0}function q(){a("update:selected",[])}function k(w,y,S,B){a("selection",{rows:y,added:S,keys:w,evt:B});const V=i.value===!0?S===!0?y:[]:S===!0?e.selected.concat(y):e.selected.filter(O=>w.includes(c.value(O))===!1);a("update:selected",V)}return{hasSelectionMode:v,singleSelection:i,multipleSelection:d,allRowsSelected:f,someRowsSelected:m,rowsSelectedNumber:o,isRowSelected:b,clearSelection:q,updateSelection:k}}function Ie(e){return Array.isArray(e)?e.slice():[]}const fl={expanded:Array},gl=["update:expanded"];function bl(e,a){const l=E(Ie(e.expanded));j(()=>e.expanded,i=>{l.value=Ie(i)});function c(i){return l.value.includes(i)}function r(i){e.expanded!==void 0?a("update:expanded",i):l.value=i}function v(i,d){const f=l.value.slice(),m=f.indexOf(i);d===!0?m===-1&&(f.push(i),r(f)):m!==-1&&(f.splice(m,1),r(f))}return{isRowExpanded:c,setExpanded:r,updateExpanded:v}}const ml={visibleColumns:Array};function hl(e,a,l){const c=u(()=>{if(e.columns!==void 0)return e.columns;const d=e.rows[0];return d!==void 0?Object.keys(d).map(f=>({name:f,label:f.toUpperCase(),field:f,align:Ce(d[f])?"right":"left",sortable:!0})):[]}),r=u(()=>{const{sortBy:d,descending:f}=a.value;return(e.visibleColumns!==void 0?c.value.filter(o=>o.required===!0||e.visibleColumns.includes(o.name)===!0):c.value).map(o=>{const b=o.align||"right",q=`text-${b}`;return{...o,align:b,__iconClass:`q-table__sort-icon q-table__sort-icon--${b}`,__thClass:q+(o.headerClasses!==void 0?" "+o.headerClasses:"")+(o.sortable===!0?" sortable":"")+(o.name===d?` sorted ${f===!0?"sort-desc":""}`:""),__tdStyle:o.style!==void 0?typeof o.style!="function"?()=>o.style:o.style:()=>null,__tdClass:o.classes!==void 0?typeof o.classes!="function"?()=>q+" "+o.classes:k=>q+" "+o.classes(k):()=>q}})}),v=u(()=>{const d={};return r.value.forEach(f=>{d[f.name]=f}),d}),i=u(()=>e.tableColspan!==void 0?e.tableColspan:r.value.length+(l.value===!0?1:0));return{colList:c,computedCols:r,computedColsMap:v,computedColspan:i}}const ue="q-table__bottom row items-center",Xe={};We.forEach(e=>{Xe[e]={}});var Pl=A({name:"QTable",props:{rows:{type:Array,default:()=>[]},rowKey:{type:[String,Function],default:"id"},columns:Array,loading:Boolean,iconFirstPage:String,iconPrevPage:String,iconNextPage:String,iconLastPage:String,title:String,hideHeader:Boolean,grid:Boolean,gridHeader:Boolean,dense:Boolean,flat:Boolean,bordered:Boolean,square:Boolean,separator:{type:String,default:"horizontal",validator:e=>["horizontal","vertical","cell","none"].includes(e)},wrapCells:Boolean,virtualScroll:Boolean,virtualScrollTarget:{default:void 0},...Xe,noDataLabel:String,noResultsLabel:String,loadingLabel:String,selectedRowsLabel:Function,rowsPerPageLabel:String,paginationLabel:Function,color:{type:String,default:"grey-8"},titleClass:[String,Array,Object],tableStyle:[String,Array,Object],tableClass:[String,Array,Object],tableHeaderStyle:[String,Array,Object],tableHeaderClass:[String,Array,Object],cardContainerClass:[String,Array,Object],cardContainerStyle:[String,Array,Object],cardStyle:[String,Array,Object],cardClass:[String,Array,Object],hideBottom:Boolean,hideSelectedBanner:Boolean,hideNoData:Boolean,hidePagination:Boolean,onRowClick:Function,onRowDblclick:Function,onRowContextmenu:Function,...se,...Zt,...ml,...nl,...il,...fl,...cl,...ll},emits:["request","virtualScroll",...Jt,...gl,...dl],setup(e,{slots:a,emit:l}){const c=I(),{proxy:{$q:r}}=c,v=ce(e,r),{inFullscreen:i,toggleFullscreen:d}=el(),f=u(()=>typeof e.rowKey=="function"?e.rowKey:t=>t[e.rowKey]),m=E(null),o=E(null),b=u(()=>e.grid!==!0&&e.virtualScroll===!0),q=u(()=>" q-table__card"+(v.value===!0?" q-table__card--dark q-dark":"")+(e.square===!0?" q-table--square":"")+(e.flat===!0?" q-table--flat":"")+(e.bordered===!0?" q-table--bordered":"")),k=u(()=>`q-table__container q-table--${e.separator}-separator column no-wrap`+(e.grid===!0?" q-table--grid":q.value)+(v.value===!0?" q-table--dark":"")+(e.dense===!0?" q-table--dense":"")+(e.wrapCells===!1?" q-table--no-wrap":"")+(i.value===!0?" fullscreen scroll":"")),w=u(()=>k.value+(e.loading===!0?" q-table--loading":""));j(()=>e.tableStyle+e.tableClass+e.tableHeaderStyle+e.tableHeaderClass+k.value,()=>{b.value===!0&&o.value!==null&&o.value.reset()});const{innerPagination:y,computedPagination:S,isServerSide:B,requestServerInteraction:V,setPagination:O}=ul(c,Q),{computedFilterMethod:x}=rl(e,O),{isRowExpanded:T,setExpanded:N,updateExpanded:K}=bl(e,l),W=u(()=>{let t=e.rows;if(B.value===!0||t.length===0)return t;const{sortBy:s,descending:g}=S.value;return e.filter&&(t=x.value(t,e.filter,L.value,Q)),Je.value!==null&&(t=et.value(e.rows===t?t.slice():t,s,g)),t}),Y=u(()=>W.value.length),$=u(()=>{let t=W.value;if(B.value===!0)return t;const{rowsPerPage:s}=S.value;return s!==0&&(ee.value===0&&e.rows!==t?t.length>te.value&&(t=t.slice(0,te.value)):t=t.slice(ee.value,te.value)),t}),{hasSelectionMode:D,singleSelection:C,multipleSelection:F,allRowsSelected:Z,someRowsSelected:xe,rowsSelectedNumber:de,isRowSelected:ve,clearSelection:Ye,updateSelection:J}=vl(e,l,$,f),{colList:Ze,computedCols:L,computedColsMap:Re,computedColspan:Te}=hl(e,S,D),{columnToSort:Je,computedSortMethod:et,sort:fe}=al(e,S,Ze,O),{firstRowIndex:ee,lastRowIndex:te,isFirstPage:ge,isLastPage:be,pagesNumber:le,computedRowsPerPageOptions:tt,computedRowsNumber:ae,firstPage:me,prevPage:he,nextPage:Se,lastPage:ye}=sl(c,y,S,B,O,Y),lt=u(()=>$.value.length===0),at=u(()=>{const t={};return We.forEach(s=>{t[s]=e[s]}),t.virtualScrollItemSize===void 0&&(t.virtualScrollItemSize=e.dense===!0?28:48),t});function nt(){b.value===!0&&o.value.reset()}function rt(){if(e.grid===!0)return ht();const t=e.hideHeader!==!0?$e:null;if(b.value===!0){const g=a["top-row"],h=a["bottom-row"],_={default:R=>Ve(R.item,a.body,R.index)};if(g!==void 0){const R=n("tbody",g({cols:L.value}));_.before=t===null?()=>R:()=>[t()].concat(R)}else t!==null&&(_.before=t);return h!==void 0&&(_.after=()=>n("tbody",h({cols:L.value}))),n(Qt,{ref:o,class:e.tableClass,style:e.tableStyle,...at.value,scrollTarget:e.virtualScrollTarget,items:$.value,type:"__qtable",tableColspan:Te.value,onVirtualScroll:it},_)}const s=[ut()];return t!==null&&s.unshift(t()),Ge({class:["q-table__middle scroll",e.tableClass],style:e.tableStyle},s)}function ot(t,s){if(o.value!==null){o.value.scrollTo(t,s);return}t=parseInt(t,10);const g=m.value.querySelector(`tbody tr:nth-of-type(${t+1})`);if(g!==null){const h=m.value.querySelector(".q-table__middle.scroll"),_=g.offsetTop-e.virtualScrollStickySizeStart,R=_<h.scrollTop?"decrease":"increase";h.scrollTop=_,l("virtualScroll",{index:t,from:0,to:y.value.rowsPerPage-1,direction:R})}}function it(t){l("virtualScroll",t)}function Be(){return[n(zt,{class:"q-table__linear-progress",color:e.color,dark:v.value,indeterminate:!0,trackColor:"transparent"})]}function Ve(t,s,g){const h=f.value(t),_=ve(h);if(s!==void 0)return s(pe({key:h,row:t,pageIndex:g,__trClass:_?"selected":""}));const R=a["body-cell"],P=L.value.map(p=>{const re=a[`body-cell-${p.name}`],oe=re!==void 0?re:R;return oe!==void 0?oe(st({key:h,row:t,pageIndex:g,col:p})):n("td",{class:p.__tdClass(t),style:p.__tdStyle(t)},Q(p,t))});if(D.value===!0){const p=a["body-selection"],re=p!==void 0?p(ct({key:h,row:t,pageIndex:g})):[n(we,{modelValue:_,color:e.color,dark:v.value,dense:e.dense,"onUpdate:modelValue":(oe,St)=>{J([h],[t],oe,St)}})];P.unshift(n("td",{class:"q-table--col-auto-width"},re))}const M={key:h,class:{selected:_}};return e.onRowClick!==void 0&&(M.class["cursor-pointer"]=!0,M.onClick=p=>{l("RowClick",p,t,g)}),e.onRowDblclick!==void 0&&(M.class["cursor-pointer"]=!0,M.onDblclick=p=>{l("RowDblclick",p,t,g)}),e.onRowContextmenu!==void 0&&(M.class["cursor-pointer"]=!0,M.onContextmenu=p=>{l("RowContextmenu",p,t,g)}),n("tr",M,P)}function ut(){const t=a.body,s=a["top-row"],g=a["bottom-row"];let h=$.value.map((_,R)=>Ve(_,t,R));return s!==void 0&&(h=s({cols:L.value}).concat(h)),g!==void 0&&(h=h.concat(g({cols:L.value}))),n("tbody",h)}function pe(t){return _e(t),t.cols=t.cols.map(s=>G({...s},"value",()=>Q(s,t.row))),t}function st(t){return _e(t),G(t,"value",()=>Q(t.col,t.row)),t}function ct(t){return _e(t),t}function _e(t){Object.assign(t,{cols:L.value,colsMap:Re.value,sort:fe,rowIndex:ee.value+t.pageIndex,color:e.color,dark:v.value,dense:e.dense}),D.value===!0&&G(t,"selected",()=>ve(t.key),(s,g)=>{J([t.key],[t.row],s,g)}),G(t,"expand",()=>T(t.key),s=>{K(t.key,s)})}function Q(t,s){const g=typeof t.field=="function"?t.field(s):s[t.field];return t.format!==void 0?t.format(g,s):g}const H=u(()=>({pagination:S.value,pagesNumber:le.value,isFirstPage:ge.value,isLastPage:be.value,firstPage:me,prevPage:he,nextPage:Se,lastPage:ye,inFullscreen:i.value,toggleFullscreen:d}));function dt(){const t=a.top,s=a["top-left"],g=a["top-right"],h=a["top-selection"],_=D.value===!0&&h!==void 0&&de.value>0,R="q-table__top relative-position row items-center";if(t!==void 0)return n("div",{class:R},[t(H.value)]);let P;if(_===!0?P=h(H.value).slice():(P=[],s!==void 0?P.push(n("div",{class:"q-table__control"},[s(H.value)])):e.title&&P.push(n("div",{class:"q-table__control"},[n("div",{class:["q-table__title",e.titleClass]},e.title)]))),g!==void 0&&(P.push(n("div",{class:"q-table__separator col"})),P.push(n("div",{class:"q-table__control"},[g(H.value)]))),P.length!==0)return n("div",{class:R},P)}const Oe=u(()=>xe.value===!0?null:Z.value);function $e(){const t=vt();return e.loading===!0&&a.loading===void 0&&t.push(n("tr",{class:"q-table__progress"},[n("th",{class:"relative-position",colspan:Te.value},Be())])),n("thead",t)}function vt(){const t=a.header,s=a["header-cell"];if(t!==void 0)return t(qe({header:!0})).slice();const g=L.value.map(h=>{const _=a[`header-cell-${h.name}`],R=_!==void 0?_:s,P=qe({col:h});return R!==void 0?R(P):n(Dt,{key:h.name,props:P},()=>h.label)});if(C.value===!0&&e.grid!==!0)g.unshift(n("th",{class:"q-table--col-auto-width"}," "));else if(F.value===!0){const h=a["header-selection"],_=h!==void 0?h(qe({})):[n(we,{color:e.color,modelValue:Oe.value,dark:v.value,dense:e.dense,"onUpdate:modelValue":Fe})];g.unshift(n("th",{class:"q-table--col-auto-width"},_))}return[n("tr",{class:e.tableHeaderClass,style:e.tableHeaderStyle},g)]}function qe(t){return Object.assign(t,{cols:L.value,sort:fe,colsMap:Re.value,color:e.color,dark:v.value,dense:e.dense}),F.value===!0&&G(t,"selected",()=>Oe.value,Fe),t}function Fe(t){xe.value===!0&&(t=!1),J($.value.map(f.value),$.value,t)}const ne=u(()=>{const t=[e.iconFirstPage||r.iconSet.table.firstPage,e.iconPrevPage||r.iconSet.table.prevPage,e.iconNextPage||r.iconSet.table.nextPage,e.iconLastPage||r.iconSet.table.lastPage];return r.lang.rtl===!0?t.reverse():t});function ft(){if(e.hideBottom===!0)return;if(lt.value===!0){if(e.hideNoData===!0)return;const g=e.loading===!0?e.loadingLabel||r.lang.table.loading:e.filter?e.noResultsLabel||r.lang.table.noResults:e.noDataLabel||r.lang.table.noData,h=a["no-data"],_=h!==void 0?[h({message:g,icon:r.iconSet.table.warning,filter:e.filter})]:[n(ke,{class:"q-table__bottom-nodata-icon",name:r.iconSet.table.warning}),g];return n("div",{class:ue+" q-table__bottom--nodata"},_)}const t=a.bottom;if(t!==void 0)return n("div",{class:ue},[t(H.value)]);const s=e.hideSelectedBanner!==!0&&D.value===!0&&de.value>0?[n("div",{class:"q-table__control"},[n("div",[(e.selectedRowsLabel||r.lang.table.selectedRecords)(de.value)])])]:[];if(e.hidePagination!==!0)return n("div",{class:ue+" justify-end"},bt(s));if(s.length>0)return n("div",{class:ue},s)}function gt(t){O({page:1,rowsPerPage:t.value})}function bt(t){let s;const{rowsPerPage:g}=S.value,h=e.paginationLabel||r.lang.table.pagination,_=a.pagination,R=e.rowsPerPageOptions.length>1;if(t.push(n("div",{class:"q-table__separator col"})),R===!0&&t.push(n("div",{class:"q-table__control"},[n("span",{class:"q-table__bottom-item"},[e.rowsPerPageLabel||r.lang.table.recordsPerPage]),n(Mt,{class:"q-table__select inline q-table__bottom-item",color:e.color,modelValue:g,options:tt.value,displayValue:g===0?r.lang.table.allRows:g,dark:v.value,borderless:!0,dense:!0,optionsDense:!0,optionsCover:!0,"onUpdate:modelValue":gt})])),_!==void 0)s=_(H.value);else if(s=[n("span",g!==0?{class:"q-table__bottom-item"}:{},[g?h(ee.value+1,Math.min(te.value,ae.value),ae.value):h(1,Y.value,ae.value)])],g!==0&&le.value>1){const P={color:e.color,round:!0,dense:!0,flat:!0};e.dense===!0&&(P.size="sm"),le.value>2&&s.push(n(ie,{key:"pgFirst",...P,icon:ne.value[0],disable:ge.value,onClick:me})),s.push(n(ie,{key:"pgPrev",...P,icon:ne.value[1],disable:ge.value,onClick:he}),n(ie,{key:"pgNext",...P,icon:ne.value[2],disable:be.value,onClick:Se})),le.value>2&&s.push(n(ie,{key:"pgLast",...P,icon:ne.value[3],disable:be.value,onClick:ye}))}return t.push(n("div",{class:"q-table__control"},s)),t}function mt(){const t=e.gridHeader===!0?[n("table",{class:"q-table"},[$e()])]:e.loading===!0&&a.loading===void 0?Be():void 0;return n("div",{class:"q-table__middle"},t)}function ht(){const t=a.item!==void 0?a.item:s=>{const g=s.cols.map(_=>n("div",{class:"q-table__grid-item-row"},[n("div",{class:"q-table__grid-item-title"},[_.label]),n("div",{class:"q-table__grid-item-value"},[_.value])]));if(D.value===!0){const _=a["body-selection"],R=_!==void 0?_(s):[n(we,{modelValue:s.selected,color:e.color,dark:v.value,dense:e.dense,"onUpdate:modelValue":(P,M)=>{J([s.key],[s.row],P,M)}})];g.unshift(n("div",{class:"q-table__grid-item-row"},R),n(Vt,{dark:v.value}))}const h={class:["q-table__grid-item-card"+q.value,e.cardClass],style:e.cardStyle};return(e.onRowClick!==void 0||e.onRowDblclick!==void 0)&&(h.class[0]+=" cursor-pointer",e.onRowClick!==void 0&&(h.onClick=_=>{l("RowClick",_,s.row,s.pageIndex)}),e.onRowDblclick!==void 0&&(h.onDblclick=_=>{l("RowDblclick",_,s.row,s.pageIndex)})),n("div",{class:"q-table__grid-item col-xs-12 col-sm-6 col-md-4 col-lg-3"+(s.selected===!0?" q-table__grid-item--selected":"")},[n("div",h,g)])};return n("div",{class:["q-table__grid-content row",e.cardContainerClass],style:e.cardContainerStyle},$.value.map((s,g)=>t(pe({key:f.value(s),row:s,pageIndex:g}))))}return Object.assign(c.proxy,{requestServerInteraction:V,setPagination:O,firstPage:me,prevPage:he,nextPage:Se,lastPage:ye,isRowSelected:ve,clearSelection:Ye,isRowExpanded:T,setExpanded:N,sort:fe,resetVirtualScroll:nt,scrollTo:ot,getCellValue:Q}),kt(c.proxy,{filteredSortedRows:()=>W.value,computedRows:()=>$.value,computedRowsNumber:()=>ae.value}),()=>{const t=[dt()],s={ref:m,class:w.value};return e.grid===!0?t.push(mt()):Object.assign(s,{class:[s.class,e.cardClass],style:e.cardStyle}),t.push(rt(),ft()),e.loading===!0&&a.loading!==void 0&&t.push(a.loading()),n("div",s,t)}}});const Sl={name:"PriorityChip",props:["value"],data(){return{label:"Unknown",color:"secondary",textColor:"black"}},created(){switch(this.value){case 0:this.label="Utmost",this.color="accent",this.textColor="white";break;case 1:this.label="High",this.color="warning",this.textColor="black";break;case 2:this.label="Normal",this.color="primary",this.textColor="white";break}}};function yl(e,a,l,c,r,v){return xt(),Rt(jt,Tt({color:r.color,"text-color":r.textColor,label:r.label},e.$attrs),null,16,["color","text-color","label"])}var xl=Pt(Sl,[["render",yl]]);export{xl as P,kl as Q,Pl as a};
