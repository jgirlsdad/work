/* This is a meta script to hit the census API and merge the data together with downloaded geospatial information via ogr
*/

require('dotenv').config({path: __dirname + '/../../../.env'});
const fs = require('fs-extra');
const program = require('commander');
const exec = require('child_process').exec;
const parse = require('csv-parse');
const stringify = require('csv-stringify');
const request = require('request');
// const census = require('citysdk');
var path = require('path');
var bunyan = require('bunyan');
program
	.option('-l, --load')
	.option('-r, --region <value>', 'Region to process', /^(zip_codes|congressional_districts)$/i)
	.option('-y, --year <items>', 'Year(s) to process')
  .parse(process.argv);

const custom_log = require(path.join(process.env.bic_etl_home, 'general/scripts/custom_log.js'));

let log = {};
custom_log.setup('dola_acs_etl', function(custom_logger) {
	log = custom_logger;
	try {
		log.info("Census API ETL Start");
		setup();
	} catch(e) {
		log.error("Unhandled error: " + e);
		process.exit();
	}
});

//Global variables
var census_fields = [],
line_ending = '',
platform = '',
num_processed = 0,
num_to_process = 0,
regions = [],
years = [];

function setup() {
	//Create temporary sql folder
	const tmp_sql_folder = 'tmp_sql'
	if (!fs.existsSync(tmp_sql_folder)) {
	    fs.mkdirsSync(tmp_sql_folder);
	}

	//Define whether the current machine is windows or linux, mac not necessary at this time
	platform = (process.platform === 'win32') ? 'windows' : 'linux';

	//Define line endings by machine
	line_ending = (platform === 'windows') ? '\r\n' : '\n';

	//Verify running in correct directory:
	const split_string = (platform === 'windows') ? "\\" : "/";

	//Read in the field names from csv
	const census_field_list_parser = parse({delimiter: ',', columns: true}, function(err, data) {
		census_fields = data;
		for(var i=0; i<census_fields.length; i++) {
			census_fields[i].table = census_fields[i].table.replace('b', 'B');
		}
	})
	.on('end', define_regions_years);

	census_field_list_file = path.join(process.env.bic_etl_home, "dola", "census", "data_source", "dictionaries", "census_field_list.csv");

	fs.createReadStream(census_field_list_file).pipe(census_field_list_parser);
}

function define_regions_years() {
	//Set up extraction regions and various specific values
	regions = [
	  {
	    name: 'zip_codes',
	    type: 'different',
	    file_name: 'ACS_{{year}}_5YR_ZCTA.gdb.zip',
	    layer_name: 'ACS_{{year}}_5YR_ZCTA',
	    where_clause: "geoid10 LIKE '80___' OR geoid10 LIKE '81___' OR geoid10 = '82063'",
		on_clause: "GEOID10 = csv.zip_code",
	    special_layer: { //replaces whats in layer_name for the specified year
		  "2012": "ACS2012_ZCTA_GEOGRAPHY",
		  "2018": "tl_2018_us_zcta510",
		  "2019": "tl_2019_us_zcta510",
		  "2020": "tl_2020_us_zcta510",
		  "2021": "tl_2021_us_zcta520",
	      "2022": "tl_2022_us_zcta520"
		},
		special_file_name: {
			"2022": "tl_2022_us_zcta520/tl_2022_us_zcta520.shp",
			"2021": "tl_2021_us_zcta520/tl_2021_us_zcta520.shp",
			"2020": "tl_2020_us_zcta510/tl_2020_us_zcta510.shp",
			"2019": "tl_2019_us_zcta510/tl_2019_us_zcta510.shp",
			"2018": "tl_2018_us_zcta510/tl_2018_us_zcta510.shp"
		}
	  },
	  {
	    name: 'congressional_districts',
	    type: 'different',
		special_file_name: { //replaces whats in file_name for the specified year 
			//for the 2021 and 2022 updates, confirm it is cd116. Might be cd 118. 
			"2022": 'tl_2022_us_cd116/tl_2022_us_cd116.shp',
			"2021": 'tl_2021_us_cd116/tl_2021_us_cd116.shp',
			"2020": 'tl_2020_us_cd116/tl_2020_us_cd116.shp',
			"2019": 'tl_2019_us_cd116/tl_2019_us_cd116.shp',
			"2018": 'tl_2018_us_cd116/tl_2018_us_cd116.shp',
			"2017": 'ACS_2017_5YR_CD_115.gdb.zip',
	      	"2016": 'ACS_2016_5YR_CD_115.gdb.zip',
	      	"2015": 'ACS_2015_5YR_CD_114.gdb.zip',
	      	"2014": 'ACS_2014_5YR_CD_114.gdb.zip',
	      	"2013": 'ACS_2013_5YR_CD_113.gdb.zip',
	      	"2012": 'ACS_2012_5YR_CD113.gdb.zip'
	    },
	    where_clause: "STATEFP = '08'", // Colorado is State 08
		//for the 2021 and 2022 updates, confirm it is cd116. Might be cd 118. 
		on_clause: {
			"2022": "csv.con_dist = CD116FP",
			"2021": "csv.con_dist = CD116FP",
			"2020": "csv.con_dist = CD116FP",
			"2019": "csv.con_dist = CD116FP",
			"2018": "csv.con_dist = CD116FP",
			"2017": "csv.con_dist = CD115FP",
			"2016": "csv.con_dist = CD115FP",
			"2015": "csv.con_dist = CD114FP",
			"2014": "csv.con_dist = CD114FP",
			"2013": "csv.con_dist = CD113FP",
			"2012": "csv.con_dist = CD113FP",
		},
		//for the 2021 and 2022 updates, confirm it is cd116. Might be cd 118. 
	    special_layer: {
			"2022": 'tl_2022_us_cd116',
			"2021": 'tl_2021_us_cd116',
			"2020": 'tl_2020_us_cd116',
			"2019": 'tl_2019_us_cd116',
			"2018": 'tl_2018_us_cd116',
			"2017": 'ACS_2017_5YR_CD_115',
	      	"2016": 'ACS_2016_5YR_CD_115',
	      	"2015": 'ACS_2015_5YR_CD_114',
	      	"2014": 'ACS_2014_5YR_CD_114',
	      	"2013": 'ACS_2013_5YR_CD_113',
	      	"2012": 'ACS2012_CD113_GEOGRAPHY'
	    }
	  }
	];

	//Use all regions, unless user specified a region:
	if(program.region) {
		for(var i=0; i< regions.length; i++) {
			if(program.region !== regions[i].name) {
				regions.splice(i--, 1);
			}
		}
		if(regions.length < 1) {
			log.error('Not a valid region, valid regions are zip_codes or congressional_districts. Please try again.');
			process.exit();
		}
	}

	//Establish years for which we can extract and transform the data:
	years = [
		{year: '2022', acs_year: 'acs1822'},
		{year: '2021', acs_year: 'acs1721'},
		{year: '2020', acs_year: 'acs1620'},
		{year: '2019', acs_year: 'acs1519'},
		{year: '2018', acs_year: 'acs1418'},
		{year: '2017', acs_year: 'acs1317'},
		{year: '2016', acs_year: 'acs1216'},
		{year: '2015', acs_year: 'acs1115'},
		{year: '2014', acs_year: 'acs1014'},
		{year: '2013', acs_year: 'acs0913'},
		{year: '2012', acs_year: 'acs0812'}
	];

	//transform for all years, unless user specifies a year:
	if(program.year) {
		if(program.year.indexOf(',') >= 0) {
			program.year = program.year.split(',');
		} else {
			program.year = [program.year];
		}
		let final_years = [];
		for(var input_year=0; input_year < program.year.length; input_year++) {
			for(var i=0; i<years.length; i++) {
				if(years[i].year == program.year[input_year]) {
					final_years.push(years[i]);
				}
			}
		}
		years = final_years;
	}

	for(var i in years) {
	  for(var j in regions) {
	    let year_folder = path.join(process.env.bic_etl_home, "dola", "census", 'data_transformed', 'raw', regions[j].name + '_' + years[i].year);
	    try {
			log.debug(year_folder);
	      fs.emptyDirSync(year_folder);
	    } catch(e) {
	      fs.mkdirsSync(year_folder);
	      log.warn('empty directory failed, creating directory', e);
	    }
	  }
	}

	num_to_process = years.length * regions.length;
	for(var reg = 0; reg < regions.length; reg++) {
		for(var y = 0; y < years.length; y++) {
			extract_transform_save(regions[reg], years[y]);
		}
	}
}

function build_field_code(table, column) {
	return table + '_' + column.padStart(3, '0') + 'E';
}

// Overall function to complete full ETL for a given region and year
function extract_transform_save(region, year) {
	let msg = "Starting download for " + region.name + " in " + year.year;
	log.info(msg);

	let num_saved = 1,
	all_regions = [],
	minimal_spatial_complete = false;

	// Create a CO specific geography file for a given region, from the download
	//  from census (see README for more info)
	function build_minimal_spatial() {
		let source_folder = path.join(process.env.bic_etl_home, "dola", "census", "data_source");
		const ogr_simplify_standard = 'ogr2ogr -f "ESRI Shapefile" -sql "SELECT * FROM {{layer_name}} WHERE {{where_clause}}" {{filtered_file_path}} {{data_source}}/{{file_name}}';

		let filtered_file_path = path.join(source_folder, 'temp', '{{region}}_{{year}}/{{region}}_{{year}}.shp');

		let ogr_simplify_command = ogr_simplify_standard
		.replace('{{data_source}}', source_folder)
		.replace('{{file_name}}', (region.special_file_name && region.special_file_name[year.year]) ? region.special_file_name[year.year] : region.file_name)
		.replace('{{layer_name}}', (region.special_layer && region.special_layer[year.year]) ? region.special_layer[year.year] : region.layer_name)
		.replace('{{filtered_file_path}}', filtered_file_path)
    	.replace(/\{\{region\}\}/g, region.name)
    	.replace(/\{\{year\}\}/g, year.year)
		.replace('{{where_clause}}', region.where_clause);

		let filtered_file_folder = null;
		try {
			// log.debug('filtered file folder: ' + filtered_file_path);
			// filtered_file_folder = filtered_file_path.split('/').slice(0, 3).join('/');
			filtered_file_folder = filtered_file_path.replace('{{year}}', year.year).replace('{{region}}', region.name)
			fs.emptyDirSync(filtered_file_folder);
		} catch(e) {
			log.debug('filtered file folder: ' + filtered_file_folder);
			fs.mkdirsSync(filtered_file_folder);
			log.warn('empty directory failed, creating directory', e);
		}

    var extract = exec(ogr_simplify_command, function(err, stdout, stderr) {
      	if(err) {
        	log.error('error running ogr command:', err, stdout, stderr);
    	} else {
			log.info("Created minimal geometry file for " + region.name + " " + year.year);
			minimal_spatial_complete = true;
		}
    });
	}

	// Setup the query to be run from the census_fields_list.csv file
	function setup_query() {
		let iterator = 0,
		fields = [];
		census_fields.forEach(function(field) {
			if(field.special_type) {
				++iterator;
				return;
			}

			//If pre-2015, use pre_2015 column for field list
			if(year.year < '2015' && field.pre_2015_fields) {
				field.column = field.pre_2015_fields;
				field.additions = '';
			}

			fields.push(build_field_code(field.table, field.column));

			if(field.additions) {
				let additions = field.additions.split(',');
				for(var i=0; i < additions.length; i++) {
					fields.push(build_field_code(field.table, additions[i]));
				}
			}

			if(++iterator === census_fields.length) {
				//Remove duplicates, pass to api function
				query_api(fields.filter(function(elem, pos) {
					return fields.indexOf(elem) === pos;
				}));
			}
		});
	}

	// Query the Census API for all the fields
	function query_api(fields) {
		// The api is limited to 50 fields.
		const API_MAX = 50,
		FIELDS_MAX = fields.length;
		for(var i=0; i<FIELDS_MAX; i=i+API_MAX) {
			let url = 'https://api.census.gov/data/{{year}}/acs/acs5?get=';
			url = url.replace('{{year}}', year.year);
			for(var j=i; j<i+API_MAX; j++) {
				if(fields[j]) {
					url += fields[j] + ',';
				}
			}
			url = url.substring(0, url.length-1);
			if(region.name == 'zip_codes') {
				url += '&for=zip code tabulation area:*';
			} else {
				url += '&for=congressional district:*&in=state:08';
			}

			// Recursive function to attempt extraction via API call. Save if successful.
			function make_request(url, retry_num) {
				request(url, function (err, res, body) {
					try {
						save_extract(err, res, JSON.parse(body), FIELDS_MAX/API_MAX);
					} catch(e) {
						log.info('Error in request: ' + err + ' ' + body);
						if(retry_num > 1) {
							make_request(url, retry_num-1);
						} else {
							log.error('Error with request: ' + err + " " + body + " " + url);
						}
					}
				});
			}
			make_request(url, 3);
		}
	}

	// Save the extract in a series of arrays. Filter zip codes by CO since not allowed via API.
	function save_extract(err, res, body, num_requests) {
		if(err) {
			log.error(err);
			// process.exit();
		}
		let total_msg = "Number of total rows for "+ num_saved+ " : " + (body.length - 1);
		log.info(total_msg);
		if(region.name == 'zip_codes') {
			//Filter on CO
			body = body.filter(function(elem, pos) {
				return elem[elem.length-1].indexOf("80") === 0 ||
					elem[elem.length-1].indexOf("81") === 0 ||
					elem[elem.length-1] === "82063" ||
					pos === 0;
			});
		}

		let colorado_msg = "Number of regions in CO: " + body.length;
		log.info(colorado_msg);

		//Track all fields in a series of arrays
		all_regions.push(body);

		if(num_saved++ >= num_requests) {
			 return merge_extract(all_regions);
		}
	}

	// Merge the different API calls into single objects per region, combining attributes
	function merge_extract(all_regions) {
		let merge_msg = "Merging "+region.name+" "+year.year+"...";
		log.info(merge_msg);
		function package_regions(region, fields, values) {
			for(var region_field=0; region_field<fields.length; region_field++) {
				region[fields[region_field]] = values[region_field];
			}
		}

		let full_regions = [];
		for(var i=1; i<all_regions[0].length; i++) {
			//Each region will be an object with all fields as keys
			let region_info = {};
			package_regions(region_info, all_regions[0][0], all_regions[0][i]);
			let region_id = all_regions[0][i][all_regions[0][i].length-1];
			for(var j=1; j<all_regions.length; j++) {
				let extra_values = all_regions[j].filter(function(elem, pos) {
					return region_id == elem[elem.length-1];
				});
				package_regions(region_info, all_regions[j][0], extra_values[0]);
			}
			log.info('Pushing ' + region_info["zip code tabulation area"]);
			full_regions.push(region_info);
		}
		let merge_res = "Merged "+full_regions.length+" regions for "+region.name+" "+year.year;
		log.info(merge_res);
		delete all_regions;
		return transform_extract(full_regions);
	}

	// Take the census_field_list.csv info and the census API results and merge.
	function transform_extract(full_regions) {
		let transformed_regions = [];
		for(var z=0; z<full_regions.length; z++) {
			let transformed_region = {};
			for(var c=0; c<census_fields.length; c++) {
				let field = census_fields[c];
				if(field.special_type != 'standard') {
					//If pre-2015, use pre_2015 column for field list
					if(year.year < '2015' && field.pre_2015_fields) {
						field.column = field.pre_2015_fields;
						field.additions = '';
					}

					if(field.special_type) {
						if(field.special_type === region.name) {
							transformed_region[field.name] = full_regions[z][field.column];
						}
					} else {
						transformed_region[field.name] = Number(full_regions[z][build_field_code(field.table, field.column)]);

						if(field.additions) {
							let additions = field.additions.split(',');
							for(var a=0; a < additions.length; a++) {
								transformed_region[field.name] += Number(full_regions[z][build_field_code(field.table, additions[a])]);
							}
						}
						if(transformed_region[field.name] < 0) {
							log.info("No data for " + field.name + " for zip " + full_regions[z]["zip code tabulation area"]);
							transformed_region[field.name] = '';
						}
					}
				}
			}
			transformed_regions.push(transformed_region);
		}
		let transformed_msg = 'Transformed '+region.name+' '+year.year+', saving csv...'
		log.info(transformed_msg);
		return save_to_file(transformed_regions);
	}

	// Save a SQL file for the final merge with spatial info, and save CSV of attributes
	function save_to_file(regions) {
		//Save sql
		let sql = "SELECT" + line_ending;
		for(var field in regions[0]) {
			sql += 'csv.' + field + ' AS ' + field + ',' + line_ending;
		}
		sql = sql.substring(0, sql.length - 1 - line_ending.length) + line_ending;
		sql += 'FROM' + line_ending;
		sql += region.name + '_' + year.year + line_ending;
		let temp_folder = path.join(process.env.bic_etl_home, "dola", "census", "data_source", "temp");
		sql += "JOIN '" + temp_folder + "/{{region}}_{{year}}.csv'.{{region}}_{{year}} AS csv ON {{on_clause}}";
		sql = sql
		.replace(/\{\{region\}\}/g, region.name)
		.replace(/\{\{year\}\}/g, year.year)
		.replace('{{on_clause}}', (region.on_clause && region.on_clause[year.year]) ? region.on_clause[year.year] : region.on_clause);
		let sql_file_name = 'tmp_sql/' + region.name + '_' + year.year + '.sql';
		fs.writeFileSync(sql_file_name, sql);

		//Save csv
		stringify(regions, {
			delimiter: ',',
			header: true
		}, function(err, output) {
			let file_name = path.join(temp_folder, region.name + '_' + year.year + '.csv');
			fs.writeFileSync(file_name, output);

			// Check if spatial file is ready, if not try again in 10 seconds.
			//  zip codes takes ~ 5 minutes per year.
			let attempt_merge = setInterval(() => merge_with_spatial(file_name, attempt_merge, sql_file_name), 10000);
			setTimeout(() => { clearInterval(attempt_merge)}, 600000);
		});
	}

	function merge_with_spatial(file_name, attempt_merge, file_name, sql_file_name) {
		if(!minimal_spatial_complete) {
			log.debug('minimal spatial file not yet complete, checking in 10 seconds...');
			return;
		}
		clearInterval(attempt_merge);
		let merge_msg = 'Ready to merge '+region.name+' '+year.year
		log.info(merge_msg);
		merge_spatial(region, year, sql_file_name);
	}
	// Kick of ETL
	setup_query();
	build_minimal_spatial();
}

// Merge the spatial information with the extracted attributes
function merge_spatial(region, year, sql_file_name) {
	let transformed_raw = path.join(process.env.bic_etl_home, "dola", "census", "data_transformed", "raw");
	let source_temp = path.join(process.env.bic_etl_home, "dola", "census", "data_source", "temp");
	const ogr_standard_command = 'ogr2ogr -f "ESRI Shapefile" -sql @{{sql_file_name}} ' +
		transformed_raw + '/{{region}}_{{year}}/{{region}}_{{year}}.shp ' +
		source_temp + '/{{region}}_{{year}}/{{region}}_{{year}}.shp';
	let ogr_region_year_command = ogr_standard_command
	.replace(/\{\{region\}\}/g, region.name)
	.replace(/\{\{year\}\}/g, year.year)
	.replace(/\{\{sql_file_name\}\}/g, 'tmp_sql/' + region.name + '_' + year.year + '.sql');

	var extract = exec(ogr_region_year_command, function(err, stdout, stderr) {
    if(err) {
      log.error('error running ogr command:' + err + stdout + stderr);
    }
  });

  extract.on('exit', function(code) {
		let message = 'Finished extracting ' + region.name + ' for ' +
			year.year +', '+ (num_to_process - ++num_processed) + ' left';
		log.info(message);
		zip_files(region, year);
  })
}

function final_processing(region, year) {
	if(num_to_process - num_processed == 0 && !program.load) {
			process.exit(-1);
	}

	if(program.load && region && year) {
		load(region, year);
	}
}

function zip_files(region, year) {
	transformed_path = path.join(process.env.bic_etl_home, 'dola', 'census', 'data_transformed');
	const zip_command = 'cd ' + path.join(transformed_path, 'raw') + 
		'; zip -rq ' + path.join(transformed_path, 'zipped', '{{region}}_{{year}}-510.zip') + ' {{region}}_{{year}}';
  var this_zip_command = zip_command
  .replace(/\{\{region\}\}/g, region.name)
  .replace(/\{\{year\}\}/g, year.year);

  var extract = exec(this_zip_command, function(err, stdout, stderr) {
    if(err) {
		log.error('zip error', err, stdout, stderr)
    }
  });
  extract.on('exit', function(code) {
			log.info(region.name, year.year, 'file zipped!');
			final_processing(region, year);
  })
}

function load(region, year) {
	let load_msg = 'Starting load for '+region.name+' '+year.year+ '...'
	log.info(load_msg);
	const GoogleSpreadsheet = require('google-spreadsheet');

	let doc = new GoogleSpreadsheet('187enO-0YmFXdwwlNnsxsJgOZ8E-RRVfcmAkcO4ZNTfg');

	doc.getInfo(function(err, info) {
		if(err) {
			log.info(err);
		}
	  sheet = info.worksheets[0];
	  sheet.getRows({
	    offset: 1,
	    orderby: 'title'
	  }, function(err, rows) {
			let region_found = false;
			for(var i=0; i<rows.length; i++) {
				let title_pieces = rows[i].title.split(' ');
		    let d_year = title_pieces[title_pieces.length-1];
		    let d_region = '';
		    if (title_pieces.length > 5) {
		      d_region = title_pieces.slice(1,3).join('_').toLowerCase();
		    } else {
		      d_region = title_pieces[1].toLowerCase();
		    }
				if(d_region == region.name && d_year == year.year) {
					// Run datasync load command, example
					// java -jar /home/jamesbrown/Documents/bic/GoCodeColorado-etl/scripts/datasync/DataSync-1.8.2.jar -c /home/jamesbrown/Documents/bic/GoCodeColorado-etl/scripts/datasync/config.json -m replace -t GISJob -i iku4-4bpx -f /home/jamesbrown/Documents/bic/GoCodeColorado-etl/scripts/census/data/block_groups_2016.zip
					region_found = true;
					let filename = 'data/transformed/zipped/{{region}}_{{year}}.zip'
					.replace('{{region}}', region.name)
					.replace('{{year}}', year.year);

					let load_cmd = 'java -jar ../datasync/DataSync-1.8.2.jar -c ../datasync/config.json -m replace -t GISJob -i {{id}} -f {{file}}'
					.replace('{{id}}', rows[i].datasetid)
					.replace('{{file}}', filename);

					log.debug("Running load", load_cmd);
					let load = exec(load_cmd, function(err, stdout, stderr) {
				    if(err) {
						log.error('Load error', err, stdout, stderr)
				    }
				  });
				  load.on('exit', function(code) {
						let load_res = region.name+' '+year.year+' dataset updated on CIM!'
						log.info(load_res);
						if(num_to_process - num_processed == 0) {
								process.exit(-1);
						}
				  })
					break;
				}
			}
			if(!region_found) {
				log.error("no match for", region.name, year.year);
			}

	  });

	})
}
