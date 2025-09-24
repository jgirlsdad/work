require('dotenv').config({path: __dirname + '/../../../../.env'});
const fs = require('fs');
const path = require('path');
const program = require('commander');
const parse = require('csv-parse');
const transform = require('stream-transform');
const stringify = require('csv-stringify');
const orr = require(path.resolve(path.join(process.env.bic_etl_home, 'cdos/business/nonprofit/scripts/orr.js')));
const orrc = orr({"state": "CO", "rulesPath": __dirname + "/rules/rules-sos-csi-reg-finan-principal.txt"});
//const custom_log = require(path.join(process.env.bic_etl_home, 'general/scripts/custom_log.js'));
const custom_helper = require(path.join(process.env.bic_etl_home, 'cdos', 'business', 'nonprofit', 'scripts', 'helper_transform_functions.js'));

const custom_log = require(path.join(process.env.bic_etl_home, 'general/scripts/custom_log_jlc.js'));
const jlclib = require(path.join(process.env.bic_etl_home, 'general/scripts/jlclib.js'));
let dict_file = path.resolve(process.env.bic_etl_home, 'cdos/business/nonprofit', 'defs', 'offices_3qtu-edua_src_trns_xrefs.json')


program
  .option('-f, --folderpath <n>', 'data_source')
  .option('-t, --title <n>', 'Charitable Organizations’ Offices in Colorado')
  .option('-e, --ext <n>', '.tsv')
  .option('-w, --w4x4 <n>','3qtu-edua')
  .parse(process.argv);


program.title = (program.title) ? program.title : 'Charitable Organizations’ Offices in Colorado';
let log = {};
// custom_log.setup(program.title, function(custom_logger) {
//     log = custom_logger;
//     initiate();
// })

custom_log.setup(program.title,program.w4x4, function(custom_logger) {
  log = custom_logger;
  initiate();
  })

global.nrecs=0;
global.header_process= {};
program.w4x4 = (program.w4x4) ? program.w4x4 : '3qtu-edua';
// global.stats = {}
global.source_columns = {}

function initiate() {
    log.debug("Program Started");
    global.stats = {}

    let ext = (program.ext) ? program.ext : '.tsv';
    let file_path = (program.folderpath) ? program.folderpath : path.join(process.env.bic_etl_home, 'cdos/business/nonprofit', 'data_source', 'offices.tsv');
    file_path = path.resolve(file_path);

    let outfile = path.resolve(process.env.bic_etl_home, 'cdos/business/nonprofit', 'data_transformed', 'charity_offices.csv');

    if (!fs.existsSync(file_path)) {
      log.error("Folder " + file_path + " does not exist to load TSV files for transform.");
        return;
    }
    let source_columns = jlclib.check_source_fields(log,program.title,file_path,dict_file)

    stats = jlclib.init_missing(header_columns,source_columns)

    transform_charity_offices(file_path, outfile); // Executes the processing
  }


let txtFileName = 'offices.txt';
let ynMap = { "y": 1, "n": 0 };

let header_columns = [
    "entityId",
    "entityType",
    "documentId",
//    "fein",
//    "name",
    "isParentOrganization",
    "organizationName",
 //   "firstName",
 //   "middleName",
 //   "lastName",
    "principalAddress",
    "principalCity",
    "principalCounty",
    "principalState",
    "principalZipCode",
 //   "principalZipCode4",
    "mailingAddress",
    "mailingCity",
    "mailingState",
    "mailingZipCode",
//    "mailingZipCode4",
    "phone",
    "fax",
    "website"
];

function fixCounty(str) {
    if(str.toLowerCase() == "usa" || str.toLowerCase() == "unknown") {
        str = "";
    }
    return str;
}

function is_valid_url(url){
  return url.match(/^(ht|f)tps?:\/\/[a-z0-9-\.]+\.[a-z]{2,4}\/?([^\s<>\#%"\,\{\}\\|\\\^\[\]`]+)?$/);
}

function stripNone(str) {
    return (str.toLowerCase() == "none") ? "" : str;
}

/*
 * added column names
 * normalized phone and fax numbers
 * added two zipcode4 columns
 * striped "NONE" out of zipcode and website columns
 * striped "USA" and "UNKNOWN" out of county column
 * lowercased all websites
 */
function transformation(row) {
  let entity_id_input = 'Entity Id';
  for(let key in row) {
    if(key.indexOf('Entity Id') > -1) {
      entity_id_input = key;
    }
  }
    let tRow                     = {};
    tRow["entityId"]             = row[entity_id_input];
    tRow["entityType"]           = row['Entity Type'];
    tRow["documentId"]           = row["Document Id"];
 //   tRow["fein"]                 = row['Ce Fein'].replace("-", "");
    tRow["organizationName"]     = row['Org Name'];
    tRow["isParentOrganization"] = ynMap[row['Co Cons Flg'].toLowerCase()];
 //   tRow["organizationName"]     = row['Co Bsn Name'];
 //   tRow["firstName"]            = row['Co Fname'];
 //   tRow["middleName"]           = row['Co Mname'];
 //   tRow["lastName"]             = row['Co Lname'];
    tRow["principalAddress"]     = row['Co Paddr'];
    tRow["principalCity"]        = orrc.resolve(row['Co Pcity'], row['Co Pcnty']);
    tRow["principalCounty"]      = fixCounty(row['Co Pcnty']);
    tRow["principalState"]       = row['Co Pstate'];
    tRow["principalZipCode"]     = row['Co Pzip'];
//    tRow["principalZipCode4"]    = custom_helper.getZip4(row['Co Pzip']);
    tRow["mailingAddress"]       = row['Co Maddr'];
    tRow["mailingCity"]          = row['Co Mcity'];
    tRow["mailingState"]         = row['Co Mstate'];
    tRow["mailingZipCode"]       = row['Co Mzip'];
 //   tRow["mailingZipCode4"]      = custom_helper.getZip4(row['Co Mzip']);
    tRow["phone"]                = custom_helper.fixPhoneNumber(row['Co Phone']);
    tRow["fax"]                  = custom_helper.fixPhoneNumber(row['Co Fax']);

	if (row['Co Url'].indexOf("@") != -1) {
    row['Co Url'] = "";
  }
	let tmpWebsite = stripNone(row['Co Url']).replace(",", ".").replace("http://http:", "http://").toLowerCase();
	if (tmpWebsite.indexOf("http://") == -1 ) {
		tmpWebsite = "http://" + stripNone(row['Co Url']).replace(",", ".").toLowerCase();
		if (tmpWebsite == "http://") {
			tmpWebsite = "";
		}
	}
  tRow["website"] = tmpWebsite.replace("http://http:", "http://");
	tRow["website"] = (is_valid_url(tRow["website"])) ? tRow["website"] : "";

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

/*
   This function will get the files to be transformed and perform the transform
*/
function transform_charity_offices(file_path, outfile) {
    log.debug("Files to be transformed: " + file_path);
    //Original file
    let input_stream = fs.createReadStream(file_path)
    .on('error', error_handler);
    //Transformed file
    let output_stream = fs.createWriteStream(outfile)
    .on('error', error_handler);
    //Parse input
    let charity_offices_parser = parse({
        relax: true,
        delimiter: "\t",
        columns: true
    })
    .on('error', error_handler);
    //Transform input
    let charity_offices_transformer = transform(transformation)
    .on('error', error_handler);
    //New data to output
    let charity_offices_stringifier = stringify({
        header: true,
        columns: header_columns
    })
    .on('error', error_handler);
    // Connect all streams
    input_stream.pipe(charity_offices_parser).pipe(charity_offices_transformer).pipe(charity_offices_stringifier).pipe(output_stream);

    //Once complete
    output_stream.on('finish', function() {
        log.debug('All items have been processed, final file is at: '+ outfile);
        jlclib.check_transformed_fields(log,program.title,outfile,dict_file,header_process,header_columns);
        jlclib.check_missing(log,stats,program.title,program.w4x4,0)
    });
}