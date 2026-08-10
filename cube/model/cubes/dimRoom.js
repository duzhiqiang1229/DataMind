cube(`dimRoom`, {

sql_table:`dim.dim_room`,

data_source:`default`,


dimensions:{


room_id:{
 sql:`room_id`,
 type:`number`,
 primary_key:true
},


room_sign:{
 sql:`room_sign`,
 type:`string`,
 title:"房间编号"
},


room_name:{
 sql:`room_name`,
 type:`string`,
 title:"房屋名称"
},


build_name:{
 sql:`build_name`,
 type:`string`,
 title:"楼栋"
},


property_uses:{
 sql:`property_uses`,
 type:`string`,
 title:"物业用途"
},


room_state:{
 sql:`room_state`,
 type:`number`,
 title:"房屋状态"
}

}


});