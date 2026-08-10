cube(`dimCommunity`, {

  sql_table: `dim.dim_community`,

  data_source: `default`,

  dimensions: {


    comm_id:{
      sql:`comm_id`,
      type:`number`,
      primary_key:true
    },


    comm_name:{
      sql:`comm_name`,
      type:`string`,
      title:"小区名称"
    },


    project_name:{
      sql:`project_name`,
      type:`string`,
      title:"项目名称"
    },


    city:{
      sql:`city`,
      type:`string`,
      title:"城市"
    },


    district:{
      sql:`district`,
      type:`string`,
      title:"区域"
    }

  }

});