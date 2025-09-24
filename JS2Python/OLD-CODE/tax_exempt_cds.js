require('dotenv').config({path: __dirname + '/../../../../.env'});
const fs = require('fs');
const path = require('path');
const program = require('commander');
const parse = require('csv-parse');
const transform = require('stream-transform');
const stringify = require('csv-stringify');
const moment = require('moment');
//const custom_log = require(path.join(process.env.bic_etl_home, 'general/scripts/custom_log.js'));
let txtFileName = 'tax_exempt_cds.txt';

const custom_log = require(path.join(process.env.bic_etl_home, 'general/scripts/custom_log_jlc.js'));
const jlclib = require(path.join(process.env.bic_etl_home, 'general/scripts/jlclib.js'));
let dict_file = path.resolve(process.env.bic_etl_home, 'cdos/business/nonprofit', 'defs', 'tax_exempt_cds_2z9k-uy4q_src_trns_xrefs.json')


program
	.option('-f, --folderpath <n>', 'data_source')
	.option('-t, --title <n>', 'tax_exempt_cds')
	.option('-e, --ext <n>', '.txt')
	.option('-w, --w4x4 <n>','2z9k-uy4q')
	.parse(process.argv);

program.title = (program.title) ? program.title : 'tax_exempt_cds';
global.nrecs=0;
global.header_process= {};
global.source_columns = {}

program.w4x4 = (program.w4x4) ? program.w4x4 : '2z9k-uy4q';

let log = {};
custom_log.setup(program.title,program.w4x4, function(custom_logger) {
    log = custom_logger;
    initiate();
    })

// custom_log.setup(program.title, function(custom_logger) {
//   log = custom_logger;
//   initiate();
// })

function initiate() {
    log.debug("Program Started");
	global.stats = {}

    let ext = (program.ext) ? program.ext : '.tsv';
    let file_path = (program.folderpath) ? program.folderpath : path.join(process.env.bic_etl_home, 'cdos/business/nonprofit', 'data_source', 'tax_exempt_cds.tsv');
    file_path = path.resolve(file_path);

    let outfile = path.resolve(process.env.bic_etl_home, 'cdos/business/nonprofit', 'data_transformed', 'tax_exempt_cds.csv');

    if (!fs.existsSync(file_path)) {
      log.error("Folder " + file_path + " does not exist to load TSV files for transform.");
        return;
    }
	source_columns = jlclib.check_source_fields(log,program.title,file_path,dict_file)
    stats = jlclib.init_missing(header_columns,source_columns,stats)
    transform_tax_exempt_cds(file_path, outfile); // Executes the processing
}

let header_columns = [
    "taxExemptCode",
    "description",
    "returnsType"
];

/*
 * added column names
 * cleaned "N/A", "NONE", and "UNKNOWN"
 */
function transformation(row)  {
	let irc_sectn_key = 'Irs Sectn';
	for(let key in row) {
		if(key.indexOf(irc_sectn_key) > -1) {
			irc_sectn_key = key;
		}
	}
	if (row[irc_sectn_key] == "Irs Sectn" || row[irc_sectn_key].trim() == "N/A" || row[irc_sectn_key].toLowerCase() == "none" || row[irc_sectn_key].toLowerCase() == "unknown" || row[irc_sectn_key].toLowerCase() == "undetermined" || row[irc_sectn_key].toLowerCase() == "") {
		return null;
	}
    let tRow = {};
    tRow["taxExemptCode"] = row[irc_sectn_key];
    tRow["description"]   = row["Activities"];
    tRow["returnsType"]   = row["Return Filed"];

	nrecs=nrecs+1
    if (nrecs == 1){
       global.header_process = Object.keys(tRow)
    }
	
    stats = jlclib.count_missing(tRow,row,stats)


    return tRow;
}

function error_handler(e) {
    log.error("Error mid-stream: " + e);
    setTimeout(function() {
      process.exit(1);
    }, 200);
  }


function transform_tax_exempt_cds(file_path, outfile) {
	log.debug("Files to be transformed: " + file_path);

	//Original file
	let input_stream = fs.createReadStream(file_path)
	.on('error', error_handler);
	//Transformed file
	let output_stream = fs.createWriteStream(outfile)
	.on('error', error_handler);
	//Parse input
	const tax_exempt_cds_parser = parse({
		relax: true,
		delimiter: "\t",
		columns: true
	})
	.on('error', error_handler);
	//Transform input
	const tax_exempt_cds_transformer = transform(transformation)
	.on('error', error_handler);
	//New data to output
	const tax_exempt_cds_stringifier = stringify({
		header: true,
		columns: header_columns
	})
	.on('error', error_handler);
  // Connect all streams
	input_stream.pipe(tax_exempt_cds_parser).pipe(tax_exempt_cds_transformer).pipe(tax_exempt_cds_stringifier).pipe(output_stream);

  //Once complete
	output_stream.on('finish', function() {
		log.debug('All items have been processed, final file is at: '+ outfile);
        jlclib.check_transformed_fields(log,program.title,outfile,dict_file,header_process,header_columns);
		jlclib.check_missing(log,stats,program.title,program.w4x4,0)
	});
}