cube(`dimCostItem`, {


sql_table:`dim.dim_cost_item`,


data_source:`default`,


dimensions:{


cost_id:{
 sql:`cost_id`,
 type:`number`,
 primary_key:true
},


cost_name:{
 sql:`cost_name`,
 type:`string`,
 title:"收费项目"
}


}


});