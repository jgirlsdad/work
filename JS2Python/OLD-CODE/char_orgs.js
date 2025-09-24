require('dotenv').config({path: __dirname + '/../../../../.env'});
const fs = require('fs');
const path = require('path');
const program = require('commander');
const parse = require('csv-parse');
const transform = require('stream-transform');
const stringify = require('csv-stringify');
const moment = require('moment');
const custom_log = require(path.join(process.env.bic_etl_home, 'general/scripts/custom_log_jlc.js'));

const jlclib = require(path.join(process.env.bic_etl_home, 'general/scripts/jlclib.js'));

let dict_file = path.resolve(process.env.bic_etl_home, 'cdos/business/nonprofit', 'defs', 'icqv-mi3c_src_trns_xrefs.json')

program
  .option('-f, --folderpath <n>', 'data_source')
  .option('-t, --title <n>', 'char_orgs')
  .option('-e, --ext <n>', '.tsv')
  .option('-w, --w4x4 <n>','icqv-mi3c')
  .parse(process.argv);
program.w4x4 = (program.w4x4) ? program.w4x4 : 'icqv-mi3c';
program.title = (program.title) ? program.title : 'char_orgs';
let log = {};
custom_log.setup(program.title,program.w4x4, function(custom_logger) {
log = custom_logger;
initiate();
})

function initiate() {
    log.debug("Program Started");

    let ext = (program.ext) ? program.ext : '.tsv';
    let file_path = (program.folderpath) ? program.folderpath : path.join(process.env.bic_etl_home, 'cdos/business/nonprofit', 'data_source', 'char_orgs_ext.tsv');
    file_path = path.resolve(file_path);

    let outfile = path.resolve(process.env.bic_etl_home, 'cdos/business/nonprofit', 'data_transformed', 'char_orgs_ext.csv');

    if (!fs.existsSync(file_path)) {
      log.error("Folder " + file_path + " does not exist to load TSV files for transform.");
        return;
    }

    jlclib.check_source_fields(log,program.title,file_path,dict_file)

    transform_char_orgs(file_path, outfile); // Executes the processing
}

var txtFileName = 'char_orgs_ext.txt';
var ynMap = { "y": 1, "": 0, "n": 0 };
global.nrecs=0;
global.header_process= {};
var header_columns = [
    "entityId",
    "fein",
    "name",
    "authorizedOfficer",
    "form990tCorporation",
    "extendedDueDate",
    "dateCreated",
    "fiscalYearend",
    "extensionRequestReason",
    "form8868Filed",
    "requestNo",
    "irsRequires990"
];

/*
	- added column names
	- camel case
	- changed all dates to ISO
	- changed 'y's and 'n's to 0 or 1
	- renamed second form990tcorporation field
	- removed all line breaks
*/
function transformation(row) {
  let entity_id_input = 'Entity Id';
  for(let key in row) {
    if(key.indexOf('Entity Id') > -1) {
      entity_id_input = key;
    }
  }
    
    var tRow                                     = {};
    tRow["entityId"]                             = row[entity_id_input];
    tRow["fein"]                                 = row['Ce Fein'].replace(/-/g, '');
    tRow["name"]                                 = row['Org Name'];
    tRow["authorizedOfficer"]                    = row['Ox Name'];
    tRow["form990tCorporation"]                  = (row['Ox 990t Flg'].toLowerCase().trim() in ynMap) ? ynMap[row['Ox 990t Flg'].toLowerCase().trim()] : '';
    tRow["extendedDueDate"]                      = (row['Ox Due Date'] != '') ? moment(row['Ox Due Date'], 'YYYYMMDD').format('YYYY-MM-DD') : "";
    tRow["dateFiled"]                          = (row['Ox Request Date'] != '') ? moment(row['Ox Request Date'], 'YYYYMMDD').format('YYYY-MM-DD') : "";
    tRow["fiscalYearend"]                        = (row['Ox Fy End'] != '') ? moment(row['Ox Fy End'], 'YYYYMMDD').format('YYYY-MM-DD') : "";
    //tRow["secondForm990tCorporationExtention"] = row[8];
    tRow["extensionRequestReason"]               = row['Ox Reason'].replace(/\r\n/g, " ");
    tRow["irsRequires990"]                     = (row['Ox Eor Flg'].toLowerCase().trim() in ynMap) ? ynMap[row['Ox Eor Flg'].toLowerCase().trim()] : '';
    tRow["form8868Filed"]                        = (row['Ox 8868 Flg'].toLowerCase().trim() in ynMap) ? ynMap[row['Ox 8868 Flg'].toLowerCase().trim()] : '';
    tRow["requestNo"]                        = row['Ox Request No']
    nrecs=nrecs+1
    if (nrecs == 1){
       global.header_process = Object.keys(tRow)
    }
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
function transform_char_orgs(file_path, outfile) {
    log.debug("Files to be transformed: " + file_path);
    //Original file
    let input_stream = fs.createReadStream(file_path)
    .on('error', error_handler);
    //Transformed file
    let output_stream = fs.createWriteStream(outfile)
    .on('error', error_handler);
    //Parse input
    const char_orgs_parser = parse({
        relax: true,
        delimiter: "\t",
        columns: true
    })
    .on('error', error_handler);
    //Transform input
    const char_orgs_transformer = transform(transformation)
    .on('error', error_handler);
    //New data to output
    const char_orgs_stringifier = stringify({
        header: true,
        columns: header_columns
    })
    .on('error', error_handler);
    // Connect all streams
    input_stream.pipe(char_orgs_parser).pipe(char_orgs_transformer).pipe(char_orgs_stringifier).pipe(output_stream);

    //Once complete
    output_stream.on('finish', function() {
        log.debug('All items have been processed, final file is at: '+ outfile);
        
        jlclib.check_transformed_fields(log,program.title,outfile,dict_file,header_process,header_columns);
    });
    
}

