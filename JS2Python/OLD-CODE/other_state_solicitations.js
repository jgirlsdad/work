/*
   Secretary Of State CSI States ETL Script
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
//const { log } = require('console');
//const custom_log = require(path.join(process.env.bic_etl_home, 'general/scripts/custom_log.js'));

const custom_log = require(path.join(process.env.bic_etl_home, 'general/scripts/custom_log_jlc.js'));


const jlclib = require(path.join(process.env.bic_etl_home, 'general/scripts/jlclib.js'));

let dict_file = path.resolve(process.env.bic_etl_home, 'cdos/business/nonprofit', 'defs', '5wyf-xqw7_src_trns_xrefs.json')



program
  .option('-f, --folderpath <n>', 'data_source')
  .option('-t, --title <n>', 'state')
  .option('-e, --ext <n>', '.tsv')
  .option('-w, --w4x4 <n>','5wyf-xqw7')
  .parse(process.argv);

program.w4x4 = (program.w4x4) ? program.w4x4 : '5wyf-xqw7';
program.title = (program.title) ? program.title : 'state';
//let log = {};
//custom_log.setup(program.title, function(custom_logger) {
//log = custom_logger;
//initiate();
//})
global.source_columns = {}
//log = {}
custom_log.setup(program.title,program.w4x4, function(custom_logger) {
  log = custom_logger;
  initiate();
  })
  
  
  global.nrecs=0;
  global.header_process= {};
  global.stats = {}

function initiate() {
    log.debug("Program Started");

    let ext = (program.ext) ? program.ext : '.tsv';
    let file_path = (program.folderpath) ? program.folderpath : path.join(process.env.bic_etl_home, 'cdos/business/nonprofit', 'data_source', 'states.tsv');
    file_path = path.resolve(file_path);

    let outfile = path.resolve(process.env.bic_etl_home, 'cdos/business/nonprofit', 'data_transformed', 'state.csv');

    if (!fs.existsSync(file_path)) {
      log.error("Folder " + file_path + " does not exist to load TSV files for transform.");
        return;
    }
    let source_columns = jlclib.check_source_fields(log,program.title,file_path,dict_file)
   

    stats['source'] = {}
    stats['transformed'] = {}
    
    for (let nn in header_columns)  {
        key = header_columns[nn]
        stats['transformed'][key] = {}
        stats['transformed'][key]['total'] = 0
        stats['transformed'][key]['missing'] = 0
    
    }
    
    for (let nn in source_columns)  {
      key = source_columns[nn]
      stats['source'][key] = {}
      stats['source'][key]['total'] = 0
      stats['source'][key]['missing'] = 0
    
    }
   
    transform_state(file_path, outfile); // Executes the processing

   // console.log(stats)
}

let ynMap = { "y": 1,"n": 0};
let entityTypeObj = {
    "PS": "Paid Solicitor",
    "PFC": "Professional Fundraising Consultant",
    "CO": "Charitable Organization"
}

let header_columns = [
    "entityId",
    "documentId",
    "fein",
    "name",
    "stateAbbreviation",
    "authorizedSoliciting",
  //  "registrantTypeAbbr",
    "registrantType"
];

//  Set up Checks for missing data



/*
 * added column names
 * camel cased names and cities
 * normalized phonenumbers
 * removed violation and organization columns
 * removed any "N/A", "NONE", or "UKNOWN" values
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
    tRow["documentId"]               = row["Document Id"];
    tRow["fein"]                 = (row["Ce Fein"]) ? row["Ce Fein"].replace(/-/g, ''): undefined;
    tRow["name"]                 = row["Org Name"];
    tRow["stateAbbreviation"]    = row["Cs State"];
  
    //tRow["authorizedSoliciting"] = (ynMap[row["Cs Auth Flg"].toLowerCase()]) ? ynMap[row["Cs Auth Flg"].toLowerCase()]: undefined;
  //  tRow["authorizedSoliciting"] = ynMap[row["Cs Auth Flg"].toLowerCase()]
    tRow["authorizedSoliciting"] = row["Cs Auth Flg"]

 //   tRow["registrantTypeAbbr"]   = row["Entity Type"];
    tRow["registrantType"]       = entityTypeObj[row["Entity Type"]];
    nrecs=nrecs+1
    if (nrecs == 1){
       global.header_process = Object.keys(tRow)
    }
    
    for (col in tRow) {
      stats['transformed'][col]['total']= stats['transformed'][col]['total']+ 1
      if (typeof(tRow[col]) == 'undefined'  || typeof(tRow[col]) == 'null' ||            (typeof(tRow[col]) == 'string' && tRow[col].length == 0) || (typeof(tRow[col]) == 'number' && tRow[col] !== tRow[col])) {
        stats['transformed'][col]['missing']=stats['transformed'][col]['missing']+1
      }
    }

    for (col in row) {
      stats['source'][col]['total']= stats['source'][col]['total'] + 1
      if (typeof(row[col]) == 'undefined'  || typeof(row[col]) == 'null' || (typeof(row[col]) == 'string' && row[col].length == 0) || (typeof(row[col]) == 'number' && row[col] !== row[col])) {
        stats['source'][col]['missing']=stats['source'][col]['missing']+1
      }
      
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
function transform_state(file_path, outfile) {
    log.debug("Files to be transformed: " + file_path);
    //Original file
    let input_stream = fs.createReadStream(file_path)
    .on('error', error_handler);
    //Transformed file
    let output_stream = fs.createWriteStream(outfile)
    .on('error', error_handler);
    //Parse input
    const state_parser = parse({
        relax: true,
        delimiter: "\t",
        columns: true
    })
    .on('error', error_handler);
    //Transform input
    const state_transformer = transform(transformation)
    .on('error', error_handler);
    //New data to output
    const state_stringifier = stringify({
        header: true,
        columns: header_columns
    })
    .on('error', error_handler);
    // Connect all streams
    input_stream.pipe(state_parser).pipe(state_transformer).pipe(state_stringifier).pipe(output_stream);


    //Once complete
    output_stream.on('finish', function() {
        log.debug('All items have been processed, final file is at: '+ outfile);
        jlclib.check_transformed_fields(log,program.title,outfile,dict_file,header_process,header_columns);

        for (let how in stats) {
          for (let col in stats[how]) {
            // if (stats[how][col]['totl'] > 0 && stats[how[col]['total'] == stats[how][col]['missing']]) {
              if (stats[how][col]['missing'] == stats[how][col]['total'] && stats[how][col]['total'] > 0) {
              log.warn("All Records Missing for " + how,col + " Total recs " + stats[how][col]['total'] +     "   Missing recs " + stats[how][col]['missing'])
            }
          }
        }
      
    });


}
