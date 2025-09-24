require('dotenv').config({path: __dirname + '/../../../../.env'});
const fs = require('fs');
const path = require('path');
const program = require('commander');
const parse = require('csv-parse');
const transform = require('stream-transform');
const stringify = require('csv-stringify');
const moment = require('moment');
const custom_log = require(path.join(process.env.bic_etl_home, 'general/scripts/custom_log.js'));
const custom_helper = require(path.join(process.env.bic_etl_home, 'cdos', 'business', 'nonprofit', 'scripts', 'helper_transform_functions.js'));

program
  .option('-f, --folderpath <n>', 'data_source')
  .option('-t, --title <n>', 'sol_ntcs_loc')
  .option('-e, --ext <n>', '.tsv')
  .parse(process.argv);

program.title = (program.title) ? program.title : 'sol_ntcs_loc';
let log = {};
custom_log.setup(program.title, function(custom_logger) {
  log = custom_logger;
  try{
    initiate();
  } catch(e) {
    log.error("Unhandled error: " + e);
    process.exit();
  }
})

function initiate() {
    log.debug("Program Started");

    let ext = (program.ext) ? program.ext : '.tsv';
    let file_path = (program.folderpath) ? program.folderpath : path.join(process.env.bic_etl_home, 'cdos/business/nonprofit', 'data_source', 'sol_ntcs_loc.tsv');
    file_path = path.resolve(file_path);

    let outfile = path.resolve(process.env.bic_etl_home, 'cdos/business/nonprofit', 'data_transformed', 'sol_ntcs_loc.csv');

    if (!fs.existsSync(file_path)) {
      log.error("Folder " + file_path + " does not exist to load TSV files for transform.");
        return;
    }

    transform_sol_ntcs_loc(file_path, outfile); // Executes the processing
}

let txtFileName = 'sol_ntcs_loc.txt';

let header_columns = [
    "solicitationNoticeId",
    "charityName",
    "charityEntityId",
    "solicitorName",
    "solicitorEntityId",
    "solicitationAddress",
    "solicitationCity",
    "solicitationState",
    "solicitationZipcode",
    "solicitationZipcode4",
    "solicitationUsedPhonenumber"
];

/*
 * added column names
 * normalized phonenumbers
 * added zipcode4 column
 * removed any "N/A", "NONE", or "UKNOWN" values
 */
function transformation(row) {
  let sol_not_id_input = 'Sols Notice Id';
  for(let key in row) {
    if(key.indexOf('Sols Notice Id') > -1) {
      sol_not_id_input = key;
    }
  }
  for(let i = 0; i< row.length; i++) {
      if(row[i] == "N/A" || row[i].toLowerCase() == "none" || row[i].toLowerCase() == "unknown") {
          row[i] = "";
      }
  }
  let tRow                            = {};
  tRow["solicitationNoticeId"]        = row[sol_not_id_input];
  tRow["charityName"]                 = row['Ce Name'];
  tRow["charityEntityId"]             = row['Entity Id Org'];
  tRow["solicitorName"]               = row['PS Name'];
  tRow["solicitorEntityId"]           = row['Entity Id Sol'];
  tRow["solicitationAddress"]         = row['Nl Paddr'];
  tRow["solicitationCity"]            = row['Nl Pcity'];
  tRow["solicitationState"]           = row['Nl Pstate'];
  tRow["solicitationZipcode"]         = custom_helper.getZipBase(row['Nl Pzip']);
  tRow["solicitationZipcode4"]        = custom_helper.getZip4(row['Nl Pzip']);
  tRow["solicitationUsedPhonenumber"] = custom_helper.fixPhoneNumber(row['Nl Phone']);

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
function transform_sol_ntcs_loc(file_path, outfile) {
    log.debug("Files to be transformed: " + file_path);
    //Original file
    let input_stream = fs.createReadStream(file_path)
    .on('error', error_handler);
    //Transformed file
    let output_stream = fs.createWriteStream(outfile)
    .on('error', error_handler);
    //Parse input
    const sol_ntcs_loc_parser = parse({
      relax: true,
        delimiter: "\t",
        columns: true
    })
    .on('error', error_handler);
    //Transform input
    const sol_ntcs_loc_transformer = transform(transformation)
    .on('error', error_handler);
    //New data to output
    const sol_ntcs_loc_stringifier = stringify({
        header: true,
        columns: header_columns
    })
    .on('error', error_handler);
    // Connect all streams
    input_stream.pipe(sol_ntcs_loc_parser).pipe(sol_ntcs_loc_transformer).pipe(sol_ntcs_loc_stringifier).pipe(output_stream);

    //Once complete
    output_stream.on('finish', function() {
        log.debug('All items have been processed, final file is at: '+ outfile);
    });
}
