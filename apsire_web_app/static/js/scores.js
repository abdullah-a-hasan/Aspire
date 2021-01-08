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
			var algs = data.scores;
			for (index in algs) {
				//if (index > 10) break;
				var src_text =  data.raw_text.src_strings[index];
				var alts_count = algs[index].top_matches.length;
				var src_order = parseInt(index)+1;
				min_sem = data['meta']['options']['minimum_semantic_score'];
				var avg = 0;
				var sem = 0;
				var len = 0;
				var loc = 0;
				var meta = 0;
				var src_mt_text = data.raw_text.src_mt_strings[index];
				var tar_text = "";
				var tar_mt_text = "";				
				var alts_btn = "<button id=\"alts_button_{0}\" disabled>...</button>";
				var tar_order = -1;
				if(alts_count > 0){
					tar_text = data.raw_text.tar_strings[algs[index].top_matches[0].tar_index];
					tar_mt_text = data.raw_text.tar_mt_strings[algs[index].top_matches[0].tar_index];
					avg = algs[index].top_matches[0].scores.avg;
					sem = algs[index].top_matches[0].scores.sem;
					len = algs[index].top_matches[0].scores.len;
					loc = algs[index].top_matches[0].scores.loc;
					meta = algs[index].top_matches[0].scores.meta;
					tar_order = parseInt(algs[index]['top_matches'][0]['tar_index'])+1;
					alts_btn = "<button id=\"alts_button_{0}\" onclick=\"generate_alts_sub_table({1})\">...</button>".format(index,index);
					var sem_pass = true; //whether semantic score passes the minimum requirements
					if(sem < min_sem) sem_pass = false;								
				}
				else{
					sem_pass = false;
				}
				var comp1_text = src_mt_text ? src_mt_text : src_text;
				var comp2_text = tar_mt_text ? tar_mt_text : tar_text;				
			  var row_node = alg_table.row.add([
				  parseInt(index), 
				  src_order,
				  (src_text != "" ? src_text : "<i>--empty--<i>"),
				  (sem_pass ? tar_order : ""),
				  (sem_pass ? tar_text : ""),
				  (sem_pass ? tar_mt_text : ""),
				  (sem_pass ? show_diff(comp1_text,comp2_text) : ""),
				  //(sem_pass ? show_diff(src_text,tar_mt_text) : ""),
				  (sem_pass ? str_to_friendly_float(avg) : ""),
				  (sem_pass ? str_to_friendly_float(sem) : ""),
				  (sem_pass ? str_to_friendly_float(len) : ""),
				  (sem_pass ? str_to_friendly_float(loc) : ""),
				  (sem_pass ? str_to_friendly_float(meta) : ""),
				  alts_btn
				  ]).node();
			  //if(sem < min_sem) $(row_node).css('background-color','#b27a70');							  
			  if(algs[index].is_anchor) $(row_node).addClass('anchor');
			  if(sem < min_sem){
				//$(row_node).hide();
				$(row_node).addClass('low-sem');
			  }
			  if(algs[index].is_translatable == false){
				//$(row_node).hide();
				$(row_node).addClass('non-trans');
			  } 

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
		//Select event
		alg_table.on( 'select', function ( e, dt, type, indexes ) {
				if ( type === 'row' ) {
					var data = alg_table.rows( indexes ).data();
					console.log('id',data[0][0]);
				}
		});	
		//Search event
		$.fn.dataTable.ext.search.push(
			function (settings, searchData, index, rowData, counter) {
			  if(settings.sInstance == "alignments_table")
			  {
				  var show_low_sem_checked = $('#show_low_sem').is(':checked');
				  var show_non_trans_checked = $('#show_non_trans').is(':checked');
				  
				  // If checked and Position column is blank don't display the row
				  if (!show_low_sem_checked && $(alg_table.row(index).node()).hasClass('low-sem')) {
					return false;
				  }

				  if (!show_non_trans_checked && $(alg_table.row(index).node()).hasClass('non-trans')) {
					return false;
				  }
			   }
			  // Otherwise display the row
			  return true;
			  
			});
		   //------------
		  //Show/hide checkbox events
		  $('#show_low_sem,#show_non_trans').on('change', function () {
			
			// Run the search plugin
			alg_table.draw();
			
		  });			
	
	//------------
	$("#toggle_diagnostics").click(function(){
		$("#debug_info").toggle();
	});
	//------------
	
}); //end of $(document).ready

//helper functions
function generate_alts_sub_table(index){
	//console.log("Showing alts for:",index);
	$("#alts_table > tbody").empty();
	
	var alts_table = $('#alts_table').DataTable({
		columnDefs: [{"visible": false, "targets":[0,1]}],
		order: [[ 0, 'desc' ], [ 6, 'desc' ]],
		retrieve: true,
		//columnDefs: [{"visible": false, "targets":0}],
		select: 'single'
	});
	alts_table.clear().draw();
	var src_text = data.raw_text.src_strings[index];//data.raw_text.src_strings[data.scores[index].src_index];
	var alts = data.scores[index].top_matches;
	//counter = 0;
	for (sub_index in alts){
		var tar_index = alts[sub_index].tar_index;
		var tar_text = data.raw_text.tar_strings[tar_index];
		var src_mt_text = data.raw_text.src_mt_strings[index]
		var tar_mt_text = data.raw_text.tar_mt_strings[tar_index];
		var comp1_text = src_mt_text ? src_mt_text : src_text;
		var comp2_text = tar_mt_text ? tar_mt_text : tar_text;
		var avg = alts[sub_index].scores.avg;
		var sem = alts[sub_index].scores.sem;
		var len = alts[sub_index].scores.len;
		var loc = alts[sub_index].scores.loc;
		var meta = alts[sub_index].scores.meta;
		var min_sem = data.meta.options.minimum_semantic_score;
		var approved_match_index = -1;
		//Decide which match index is the approved one (checking for manual approval first)
		if(data.scores[index].hasOwnProperty('approved_match_index')){
			approved_match_index = data.scores[index]['approved_match_index'];
		}
		else if(data.scores[index].is_translatable && sem >= min_sem){
			approved_match_index = 0;
		}
		
		//console.log(parseInt(tar_index)+1,tar_text,tar_mt_text,show_diff(src_text,tar_mt_text),str_to_friendly_float(avg),str_to_friendly_float(sem),str_to_friendly_float(len),str_to_friendly_float(loc));
		row_node = alts_table.row.add([
					(approved_match_index == sub_index ? 1 : 0),
					sub_index, // index within the top_matches array
					parseInt(tar_index)+1, // friendly order of tar segment
					tar_text,
					tar_mt_text,
					//show_diff(src_text,tar_mt_text),
					show_diff(comp1_text,comp2_text),
					str_to_friendly_float(avg),
					str_to_friendly_float(sem),
					str_to_friendly_float(len),
					str_to_friendly_float(loc),
					str_to_friendly_float(meta)]).node();
		if(approved_match_index == sub_index)
			$(row_node).addClass('approved_alt');
		/*if(sem < min_sem)
			$(row_node).addClass('low-sem');*/
	}
	alts_table.draw();
	$("#alts_source_order").text(index+1);
	$("#alts_source_text").text(src_text);
	$("#alts_source_index").val(index);
	dialog = $('#sub_tables').modal();
	$('.modal').css({maxWidth:"90%"});
} //End generate and show alts dialog & table

//Helper functions

//Decide each text column's direction based on its language
function set_rtl_if_needed(){
	if (data.meta.source_language == 'ar'){
		$("#alignments_table td:nth-child(2)").addClass('rtl');
	}
	if (data.meta.target_language == 'ar'){
		$("#alignments_table td:nth-child(4)").addClass('rtl');
	}
	if (data.meta.target_mt_language == 'ar'){
		$("#alignments_table td:nth-child(5)").addClass('rtl');
	}
}

//Extend string object
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

function show_diff(str1,str2){
	var wikEdDiff = new WikEdDiff();
	diff_html = wikEdDiff.diff(str1, str2);
	return diff_html;
	//return '';
	var comp = new diff_match_patch();
	var result = comp.diff_main(str1, str2);
	comp.diff_cleanupSemantic(result);
	return comp.diff_prettyHtml(result);
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