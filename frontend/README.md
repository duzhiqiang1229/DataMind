# DataMind Frontend

## 技术栈
- Vue 3.5 + TypeScript + Vite 6
- Element Plus (UI)
- ECharts (图表)
- Pinia (状态管理, 持久化)
- Vue Router 4
- Axios (HTTP)

## 工程结构

```
frontend/
├── src/
│   ├── main.ts                    # 应用入口
│   ├── App.vue                    # 根组件
│   ├── api/                       # API 封装层
│   │   ├── request.ts             #   Axios 实例 + 拦截器
│   │   └── index.ts               #   API 模块 (auth/datasource/datax/query...)
│   ├── assets/
│   │   └── styles/
│   │       ├── index.scss         #   全局样式
│   │       └── variables.scss     #   SCSS 变量
│   ├── components/                 # 公共组件
│   ├── layouts/
│   │   └── MainLayout.vue         # 主布局 (侧边栏+头部+内容区)
│   ├── router/
│   │   └── index.ts               # 路由 + 导航守卫
│   ├── stores/
│   │   └── auth.ts                 # 认证状态 (token/userInfo/permissions)
│   ├── types/                     # TypeScript 类型定义
│   ├── utils/                     # 工具函数
│   └── views/                     # 页面
│       ├── login/index.vue        #   登录页
│       ├── dashboard/index.vue    #   首页驾驶舱
│       ├── datasource/index.vue   #   数据源管理
│       ├── datax/index.vue        #   DataX 同步任务
│       ├── query/index.vue        #   SQL 工作台
│       └── system/user/index.vue  #   用户管理
├── package.json
├── vite.config.ts
├── tsconfig.json
└── index.html
```

## 页面清单 (MVP)

| 页面 | 路由 | 功能 |
|------|------|------|
| 登录 | /login | 用户名密码登录 |
| 首页驾驶舱 | /dashboard | 统计卡片 + 趋势图 + 最近任务 + 组件状态 |
| 数据源管理 | /datasource | 数据源CRUD + 连接测试 |
| DataX 同步 | /datax | 任务CRUD + 触发执行 + 执行历史 |
| SQL 工作台 | /query | 库表浏览 + SQL编辑器 + 结果展示 |
| 用户管理 | /system/user | 用户CRUD + 角色分配 |

## API 代理
Vite dev server 代理 `/api` 到 `http://localhost:8000` (后端 FastAPI)

## 运行
```bash
cd frontend
npm install
npm run dev      # 开发: http://localhost:5173
npm run build    # 构建: dist/
```
