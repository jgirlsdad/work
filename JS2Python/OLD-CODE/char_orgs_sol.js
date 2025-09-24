require('dotenv').config({path: __dirname + '/../../../../.env'});
const fs = require('fs');
const path = require('path');
const program = require('commander');
const parse = require('csv-parse');
const transform = require('stream-transform');
const stringify = require('csv-stringify');
const moment = require('moment');
const jlclib = require(path.join(process.env.bic_etl_home, 'general/scripts/jlclib.js'));

const orr = require(path.resolve(path.join(process.env.bic_etl_home, 'cdos/business/nonprofit/scripts/orr.js')));
const orrc = orr({"state": "CO", "rulesPath": __dirname + "/rules/rules-sos-csi-persons-entity-principal.txt"});
// const custom_log = require(path.join(process.env.bic_etl_home, 'general/scripts/custom_log.js'));
const custom_log = require(path.join(process.env.bic_etl_home, 'general/scripts/custom_log_jlc.js'));

const custom_helper = require(path.join(process.env.bic_etl_home, 'cdos', 'business', 'nonprofit', 'scripts', 'helper_transform_functions.js'));

let dict_file = path.resolve(process.env.bic_etl_home, 'cdos/business/nonprofit', 'defs', 'char_orgs_sol_wwbh-7bpa_src_trns_xrefs.json')

program
  .option('-f, --folderpath <n>', 'data_source')
  .option('-t, --title <n>', 'char_orgs_sol')
  .option('-e, --ext <n>', '.tsv')
  .option('-w, --w4x4 <n>','wwbh-7bpa')

  .parse(process.argv);

program.title = (program.title) ? program.title : 'char_orgs_sol';
global.nrecs=0;
global.header_process= {};
global.source_columns = {}
global.stats = {}

program.w4x4 = (program.w4x4) ? program.w4x4 : 'wwbh-7bpa';
let log = {};
// custom_log.setup(program.title, function(custom_logger) {
// log = custom_logger;
// initiate();
// })

custom_log.setup(program.title,program.w4x4, function(custom_logger) {
  log = custom_logger;
  initiate();
  })




function initiate() {
    log.debug("Program Started");

    let ext = (program.ext) ? program.ext : '.tsv';
    let file_path = (program.folderpath) ? program.folderpath : path.join(process.env.bic_etl_home, 'cdos/business/nonprofit', 'data_source', 'char_orgs_sol.tsv');
    file_path = path.resolve(file_path);

    let outfile = path.resolve(process.env.bic_etl_home, 'cdos/business/nonprofit', 'data_transformed', 'char_orgs_sol.csv');

    if (!fs.existsSync(file_path)) {
      log.error("Folder " + file_path + " does not exist to load TSV files for transform.");
        return;
    }
    source_columns = jlclib.check_source_fields(log,program.title,file_path,dict_file)
    stats = jlclib.init_missing(header_columns,source_columns,stats)
    transform_char_orgs_sol(file_path, outfile); // Executes the processing
}

let txtFileName = 'char_orgs_sol.txt';
const ynMap = { "y": 1, "n": 0 };
// const personTypeObj = {
//     "PS": "Paid Solicitor",
//     "PFC": "Professional Fundraising Consultant"
// }

let header_columns = [
    "entityId",
    "documentId",
    "fein",
    "name",
    "nameofPS-PFC-CCV",
    "title",
    "firstName",
    "middleName",
    "lastName",
 //   "registrantTypeAbbr",
    "registrantType",
    "address",
    "city",
    "state",
    "zipCode",
//    "zipCode4",
    "mailingAddress",
    "mailingCity",
    "mailingState",
    "mailingZipCode",
 //   "mailingZipCode4",
    "performedAddress",
    "performedCity",
    "performedState",
    "performedZipCode",
//    "performedZipCode4",
    "phone"
];


function transformation(row) {
  let entity_id_input = 'Entity Id';
  for(let key in row) {
    if(key.indexOf('Entity Id') > -1) {
      entity_id_input = key;
    }
  }

    let tRow                   = {};
    tRow["entityId"]           = row[entity_id_input];
    tRow["documentId"]             = row['Document Id'];
    tRow["fein"]               = row['Ce Fein'].replace(/-/g, '');
    tRow["name"]               = row['Org Name'];
    tRow["nameofPS-PFC-CCV"] = row['Ol Org Name'];
    tRow["title"]              = row['Ol Title'];
    tRow["firstName"]          = custom_helper.fixCap(row['Ol Fname']);
    tRow["middleName"]         = custom_helper.fixCap(row['Ol Mname']);
    tRow["lastName"]           = custom_helper.fixCap(row['Ol Lname']);
//    tRow["registrantTypeAbbr"] = row['Person Type'];
    tRow["registrantType"]     = row['Person Type'];
    tRow["address"]            = row['Address'];
    tRow["city"]               = orrc.resolve(row['City'], row['State']);
    tRow["state"]              = row['State'];
    tRow["zipCode"]            = row['Zip'];
    tRow["mailingAddress"]     = row['Ol Maddr'];
    tRow["mailingCity"]        = custom_helper.fixCap(row['Ol Mcity']);
    tRow["mailingState"]       = row['Ol Mstate'];
    tRow["mailingZipCode"]     = row['Ol Mzip'];
    tRow["performedAddress"]   = row['Ol Waddr'];
    tRow["performedCity"]      = custom_helper.fixCap(row['Ol Wcity']);
    tRow["performedState"]     = row['Ol Wstate'];
    tRow["performedZipCode"]   = row['Ol Wzip'];
    tRow["phone"]              = custom_helper.fixPhoneNumber(row['Ol Wphone']);

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
function transform_char_orgs_sol(file_path, outfile) {
    log.debug("Files to be transformed: " + file_path);
    //Original file
    let input_stream = fs.createReadStream(file_path)
    .on('error', error_handler);
    //Transformed file
    let output_stream = fs.createWriteStream(outfile)
    .on('error', error_handler);
    //Parse input
    const char_orgs_sol_parser = parse({
        relax: true,
        delimiter: "\t",
        columns: true
    })
    .on('error', error_handler);
    //Transform input
    const char_orgs_sol_transformer = transform(transformation)
    .on('error', error_handler);
    //New data to output
    const char_orgs_sol_stringifier = stringify({
        header: true,
        columns: header_columns
    })
    .on('error', error_handler);
    // Connect all streams
    input_stream.pipe(char_orgs_sol_parser).pipe(char_orgs_sol_transformer).pipe(char_orgs_sol_stringifier).pipe(output_stream);

    //Once complete
    output_stream.on('finish', function() {
        log.debug('All items have been processed, final file is at: '+ outfile);
        jlclib.check_transformed_fields(log,program.title,outfile,dict_file,header_process,header_columns);
        jlclib.check_missing(log,stats,program.title,program.w4x4,0) 
    });
}
