cube(`dwd_fee_fees_df`, {
  sql_table: `dwd.dwd_fee_fees_df`,
  
  data_source: `default`,
  
  joins: {

      // 小区维度
    dimCommunity: {
      relationship: `belongsTo`,
      sql: `
        ${CUBE}.comm_id = ${dimCommunity}.comm_id
      `
    },


    // 房间维度
    dimRoom: {
      relationship: `belongsTo`,
      sql: `
        ${CUBE}.room_id = ${dimRoom}.room_id
      `
    },


    // 收费项目维度
    dimCostItem: {
      relationship: `belongsTo`,
      sql: `
        ${CUBE}.cost_id = ${dimCostItem}.cost_id
      `
    }
    
  },
  
  dimensions: {

    fees_id:{
      sql:`fees_id`,
      type:`number`,
      primaryKey:true,
      title:"费用ID"
   },


    build_name: {
      sql: `build_name`,
      type: `string`
    },
    
    city: {
      sql: `city`,
      type: `string`
    },
    
    comm_name: {
      sql: `comm_name`,
      type: `string`
    },
    
    cost_name: {
      sql: `cost_name`,
      type: `string`
    },
    
    cust_name: {
      sql: `cust_name`,
      type: `string`
    },
    
    customer_type: {
      sql: `customer_type`,
      type: `string`
    },
    
    district: {
      sql: `district`,
      type: `string`
    },
    
    park_name: {
      sql: `park_name`,
      type: `string`
    },
    
    park_type: {
      sql: `park_type`,
      type: `string`
    },
    
    project_name: {
      sql: `project_name`,
      type: `string`
    },
    
    property_uses: {
      sql: `property_uses`,
      type: `string`
    },
    
    room_name: {
      sql: `room_name`,
      type: `string`
    },
    
    room_sign: {
      sql: `room_sign`,
      type: `string`
    },
    
    stan_name: {
      sql: `stan_name`,
      type: `string`
    },
    
    use_state: {
      sql: `use_state`,
      type: `string`
    },
    
    dt: {
      sql: `dt`,
      type: `time`
    },
    
    fees_due_date: {
      sql: `fees_due_date`,
      type: `time`
    },
    
    fees_end_date: {
      sql: `fees_end_date`,
      type: `time`
    },
    
    fees_state_date: {
      sql: `fees_state_date`,
      type: `time`
    }
  },
  
  measures: {
    count: {
      type: `count`
    },
    
    due_amount: {
      sql: `due_amount`,
      type: `sum`
    },
    
    stan_amount: {
      sql: `stan_amount`,
      type: `sum`
    }
  },
  
  pre_aggregations: {
    // Pre-aggregation definitions go here.
    // Learn more in the documentation: https://cube.dev/docs/caching/pre-aggregations/getting-started
  }
});
