var json_url = static_url_base + 'download/' + decodeURIComponent(urlParam("json_file"));
var data = {};
var min_sem;
var alg_table;
$(document).ready(function(){
	   alg_table = $('#alignments_table').DataTable({
			//dom: 'Bfrtip',
			columnDefs: [{"visible": false, "targets":0}],
			select: 'single'
		});
		//Post form data
		$.get( json_url, function( results ) {
			//clear the table
			//console.log(results);
			//alert("here");
			data = results;
			var algs = data.alignments;
			for (index in algs) {
				var src_text = join_strs_by_indexes(algs[index].src_indexes,data.raw_text.src_strings);
				var tar_text = join_strs_by_indexes(algs[index].tar_indexes,data.raw_text.tar_strings);
				var list_order = parseInt(index)+1;
				var pass = '<button id="pass_fail_btn_{0}" title="Change to Fail" onclick=toggle_pass_fail({1})>Pass</button>'.format(index,index);
				var fail = '<button id="pass_fail_btn_{0}" title="Change to Pass" onclick=toggle_pass_fail({1})>Fail</button>'.format(index,index);

			  var row_node = alg_table.row.add([
				  parseInt(index),
				  list_order,
				  (src_text != "" ? src_text : "<i>--empty--<i>"),
				  (tar_text != "" ? tar_text : "<i>--empty--<i>"),
				  (algs[index].verdict == 'p' ? pass : fail)
				  ]).node();
			  if(algs[index].src_indexes.length > 1 || algs[index].tar_indexes.length > 1)
				  $(row_node).addClass('merged');
			  if (algs[index].verdict == 'f')
				  $(row_node).addClass('fail');
			}
			alg_table.draw();
			$("#display_alignments").show();
			//Process diagnostics
			$('#options_summary').text("Options summary:" + JSON.stringify(data.meta.options));
			//Additional formatting
			set_rtl_if_needed();
		}, "json").fail(function(){
				$("#warning").text("Could not process at this time.");
				$("#warning").show();
		}); //end get request

		//Hook events

	//------------
	$("#toggle_diagnostics").click(function(){
		$("#debug_info").toggle();
	});
	//------------
	$('#gen_tmx_btn').click(function(){
		 $('#tmx_area').html('Loading...');
		$.post(flask_api_url + 'gen-tmx', {'json_dict':JSON.stringify(data)}, function( results ){
			console.log('File name' + JSON.stringify(results));
			$('#tmx_area').html('<a target="_blank" href="' + static_url_base + 'download/' + results.tmx_file_name + '">Download TMX file</a>');
		},'json').fail(function(){
			alert('Server error');
		});
	});
	$('#gen_xls_btn').click(function(){
		 $('#xls_area').html('Loading...');
		$.post(flask_api_url + 'gen-xls', {'json_dict':JSON.stringify(data)}, function( results ){
			console.log('File name' + JSON.stringify(results));
			$('#xls_area').html('<a target="_blank" href="' + static_url_base + 'download/' + results.xls_file_name + '">Download XLS file</a>');
		},'json').fail(function(){
			alert('Server error');
		});
	});
	//------------
	//------------

}); //end of $(document).ready

//helper functions

function toggle_pass_fail(row){
	console.log('called toggle_pass_fail for row ', row);
	//var selected_row = alg_table.row( { selected: true } );
	var selected_row = alg_table.row(row);
	//$(selected_row.node()).toggleClass('fail');

	if(data.alignments[row].verdict == 'p'){
		$(selected_row.node()).addClass('fail');
		data.alignments[row].verdict = 'f';
		$("#pass_fail_btn_"+row).text('Fail');
		$('#tmx_area').html(''); //remove link to previous tmx
		console.log('Changed verdict and button text to fail');
	}
	else{
		$(selected_row.node()).removeClass('fail');
		data.alignments[row].verdict = 'p';
		$("#pass_fail_btn_"+row).text('Pass');
		$('#tmx_area').html(''); //remove link to previous tmx
		$('#xls_area').html(''); //same with xls
		console.log('Changed verdict and button text to pass');
	}

	//alg_table.draw();
}

//Decide each text column's direction based on its language
function set_rtl_if_needed(){
	if (data.meta.source_language == 'ar'){
		$("#alignments_table td:nth-child(2)").addClass('rtl');
	}
	if (data.meta.target_language == 'ar'){
		$("#alignments_table td:nth-child(3)").addClass('rtl');
	}
}

function join_strs_by_indexes(indexes_list, strs_list){
	result = '';
	for (var i = 0; i < indexes_list.length; i++) {
		result += " " + strs_list[indexes_list[i]];
	}
	return result;
}

String.prototype.format = function () {
	var a = this;
	for (var k in arguments) {
	a = a.replace(new RegExp("\\{" + k + "\\}", 'g'), arguments[k]);
	}
	return a
}
function str_to_friendly_float(str){
	return (parseFloat(str)*100).toFixed(1);
}

//Url parameter getter jQuery plugin
function urlParam (name){
	var results = new RegExp('[\?&]' + name + '=([^&#]*)').exec(window.location.href);
	if (results==null){
	   return null;
	}
	else{
	   return results[1] || 0;
	}
}