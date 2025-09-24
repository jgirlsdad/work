/*
   Secretary Of State CSI Persons Sol NTCS ETL Script
   v1.0.0
   Last Modified: 2013-12-11
*/
require('dotenv').config({path: __dirname + '/../../../../.env'});
const fs = require('fs');
const path = require('path');
const program = require('commander');
const parse = require('csv-parse');
const transform = require('stream-transform');
const stringify = require('csv-stringify');
//const custom_log = require(path.join(process.env.bic_etl_home, 'general/scripts/custom_log.js'));
const moment = require('moment');
const orr = require(path.resolve(path.join(process.env.bic_etl_home, 'cdos/business/nonprofit/scripts/orr.js')));
const orrc = orr({"state": "CO", "rulesPath": __dirname + "/rules/rules-sos-csi-sol-ntcs-principal.txt"});
const custom_helper = require(path.join(process.env.bic_etl_home, 'cdos', 'business', 'nonprofit', 'scripts', 'helper_transform_functions.js'));


const custom_log = require(path.join(process.env.bic_etl_home, 'general/scripts/custom_log_jlc.js'));
const jlclib = require(path.join(process.env.bic_etl_home, 'general/scripts/jlclib.js'));
let dict_file = path.resolve(process.env.bic_etl_home, 'cdos/business/nonprofit', 'defs', 'persons_sol_ntcs_hyr8-d3v9_src_trns_xrefs.json')


program
  .option('-f, --folderpath <n>', 'data_source')
  .option('-t, --title <n>', 'campaign_supervisors')
  .option('-e, --ext <n>', '.tsv')
  .option('-w, --w4x4 <n>','hyr8-d3v9')
  .parse(process.argv);


global.nrecs=0;
global.header_process= {};
global.source_columns = {}
global.stats = {}

program.w4x4 = (program.w4x4) ? program.w4x4 : 'hyr8-d3v9';
   
//program.title = (program.title) ? program.title : 'campaign_supervisors';
program.title = (program.title) ? program.title : 'Solicitation Campaign Supervisors Listed on Solicitation Notices in Colorado';

let log = {};
custom_log.setup(program.title,program.w4x4, function(custom_logger) {
  log = custom_logger;
  initiate();
  })

function initiate() {
    log.debug("Program Started");

    let ext = (program.ext) ? program.ext : '.tsv';
    let file_path = (program.folderpath) ? program.folderpath : path.join(process.env.bic_etl_home, 'cdos/business/nonprofit', 'data_source', 'persons_sol_ntcs_test.tsv');
    file_path = path.resolve(file_path);

    let outfile = path.resolve(process.env.bic_etl_home, 'cdos/business/nonprofit', 'data_transformed', 'campaign_supervisors.csv');

    if (!fs.existsSync(file_path)) {
      log.error("Folder " + file_path + " does not exist to load TSV files for transform.");
        return;
    }

    source_columns = jlclib.check_source_fields(log,program.title,file_path,dict_file)
    stats = jlclib.init_missing(header_columns,source_columns,stats)

    transform_campaign_supervisors(file_path, outfile); // Executes the processing
}

let txtFileName = 'persons_sol_ntcs.tsv';
let ynMap = { "y": 1, "n": 0 };
let personTypeObj = {
    "PS": "Paid Solicitor",
    "PFC": "Professional Fundraising Consultant"
};

let header_columns = [
    "solicitationNoticeId",
    "charityName",
    "solicitorName",
    "officerTitle",
    "businessName",
    "firstName",
    "middleName",
    "lastName",
    "principalAddress",
    "principalCity",
    "principalState",
    "principalZipCode",
    "phone",
    "isSubcontractor",
    "officerInBusiness",
    "otherNamesOfOrganization",
    "snId"
];

/*
	* added column names
	* camel cased names
	* added zipCode4 columns
	* camel cased city names
	* normalized phone numbers
	* cleaned "N/A", "NONE", and "UNKNOWN"
*/
function transformation(row) {
  let sol_id_key = "Sols Notice Id";
  for(let key in row) {
    if(key.indexOf(sol_id_key) > -1) {
      sol_id_key = key;
    }
  }

    let tRow                         = {};
    tRow["solicitationNoticeId"]     = row[sol_id_key];
    tRow["charityName"]              = row["Ce Name"];
    tRow["solicitorName"]            = row["PS Name"];
    tRow["officerTitle"]             = row["Cp Title"]
    tRow["businessName"]             = row["Cp Bsn Name"]
    tRow["firstName"]                = row["Cp Fname"]
    tRow["middleName"]               = row["Cp Mname"]
    tRow["lastName"]                 = row["Cp Lname"]
    tRow["principalAddress"]         = row["Address"];
    tRow["principalCity"]            = orrc.resolve(row["City"], row["City"]);
    tRow["principalState"]           = row["State"];
    tRow["principalZipCode"]         = custom_helper.getZipBase(row["Zip"])
    tRow["phone"]                    = custom_helper.fixPhoneNumber(row["Phone"]);
    tRow["isSubcontractor"]          = row["Cp Subc Flg"];
    tRow["officerInBusiness"]        = row["Cp Sol Offcr Flg"];
    tRow["otherNamesOfOrganization"] = row["Cd Dba"];
    tRow["snId"] = row["Sn Id"];
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
function transform_campaign_supervisors(file_path, outfile) {
    log.debug("Files to be transformed: " + file_path);
    //Original file
    let input_stream = fs.createReadStream(file_path)
    .on('error', error_handler);
    //Transformed file
    let output_stream = fs.createWriteStream(outfile)
    .on('error', error_handler);
    //Parse input
    const campaign_supervisors_parser = parse({
        relax: true,
        delimiter: "\t",
        columns: true
    })
    .on('error', error_handler);
    //Transform input
    const campaign_supervisors_transformer = transform(transformation)
    .on('error', error_handler);
    //New data to output
    const campaign_supervisors_stringifier = stringify({
        header: true,
        columns: header_columns
    })
    .on('error', error_handler);
    // Connect all streams
    input_stream.pipe(campaign_supervisors_parser).pipe(campaign_supervisors_transformer).pipe(campaign_supervisors_stringifier).pipe(output_stream);

    //Once complete
    output_stream.on('finish', function() {
      jlclib.check_missing(log,stats,program.title,program.w4x4,0) 
      jlclib.check_transformed_fields(log,program.title,outfile,dict_file,header_process,header_columns);
        log.debug('All items have been processed, final file is at: '+ outfile);
    });
}