$(document).ready(function(){
json_dict = {};
  $("#align_btn").click(function(){
		$("#warning").hide();
		//Validate form data
		if($("#source_ta").val().length > 70000 || $("#target_ta").val().length > 70000){
			$("#warning").text("Source or target text too large for the demo. Limit each to 50,000 characters.");
			$("#warning").show();
			return;
		}
		if($("#source_ta").val().length < 10 || $("#target_ta").val().length < 10){
			$("#warning").text("Source or target text too small.");
			$("#warning").show();
			return;
		}
		if(isNaN($("#input_semantic_weight").val())){
			$("#warning").text("'Semantic weight' should be a floating number.");
			$("#warning").show();
			return;
		}
		if(isNaN($("#input_location_weight").val())){
			$("#warning").text("'Location weight' should be a floating number.");
			$("#warning").show();
			return;
		}
		if(isNaN($("#input_length_weight").val())){
			$("#warning").text("'Length weight' should be a floating number.");
			$("#warning").show();
			return;
		}
		if(isNaN($("#input_meta_weight").val())){
			$("#warning").text("'Length weight' should be a floating number.");
			$("#warning").show();
			return;
		}		
		if(isNaN($("#input_minimum_semantic_score").val())){
			$("#warning").text("'Minimum Semantic score' should be a floating number.");
			$("#warning").show();
			return;
		}
		if(isNaN($("#input_minimum_length_score").val())){
			$("#warning").text("'Minimum length score' should be a floating number.");
			$("#warning").show();
			return;
		}
		if(isNaN($("#input_search_range").val())){
			$("#warning").text("'Search range' should be an integer.");
			$("#warning").show();
			return;
		}
		$("#align_btn").text("Working...");
		//Build form data
		var post_data = { source_text: $("#source_ta").val(),
						target_text: $("#target_ta").val(),
						target_lang: $("#target_lang").val(),
						input_semantic_weight: $("#input_semantic_weight").val(),
						input_location_weight: $("#input_location_weight").val(),
						input_length_weight: $("#input_length_weight").val(),
						input_meta_weight: $("#input_meta_weight").val(),
						input_minimum_semantic_score: $("#input_minimum_semantic_score").val(),
						input_minimum_length_score: $("#input_minimum_length_score").val(),
						input_paragraph_size: $("#input_search_range").val(),
						algorithm: $("#algorithm").val()
						};
		//Post form data
		$.post( flask_api_url + 'align', post_data, function( data ) {
			$("#align_btn").text("Align");
			//clear the table

			$('#summary').html("<a href=\"{0}review.html?json_file={1}\" target=\"_blank\">Review alignments</a>".format(static_url_base, data.json_file_name));
			$('#summary').append("<br/><a href=\"{0}scores.html?json_file={1}\" target=\"_blank\">View scores</a>".format(static_url_base, data.json_file_name));
		}, "json").fail(function(){
				$("#warning").text("Could not process at this time.");
				$("#warning").show();
				$("#align_btn").text("Align");
		});
	});

	$("#algorithm").change(function(){
		if($("#algorithm").val() == 'fuzzy'){
			$("#input_minimum_semantic_score").val('0.60');
		}
		else if($("#algorithm").val() == 'tf-idf'){
			$("#input_minimum_semantic_score").val('0.5');
		}
	});
	
	$("#toggle_advanced").click(function(){
		$("#advanced_settings").toggle();
	});

});
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