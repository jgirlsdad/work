require('dotenv').config({path: __dirname + '/../../../../.env'});
const fs = require('fs');
const path = require('path');
const program = require('commander');
const parse = require('csv-parse');
const transform = require('stream-transform');
const stringify = require('csv-stringify');
const custom_log = require(path.join(process.env.bic_etl_home, 'general/scripts/custom_log.js'));
const moment = require('moment');

program
  .option('-f, --folderpath <n>', 'data_source')
  .option('-t, --title <n>', 'purpose')
  .option('-e, --ext <n>', '.tsv')
  .parse(process.argv);

program.title = (program.title) ? program.title : 'sol_typ_sol_ntcs';
let log = {};
custom_log.setup(program.title, function(custom_logger) {
log = custom_logger;
initiate();
})

function initiate() {
    log.debug("Program Started");

    let ext = (program.ext) ? program.ext : '.tsv';
    let file_path = (program.folderpath) ? program.folderpath : path.join(process.env.bic_etl_home, 'cdos/business/nonprofit', 'data_source', 'sol_typ_sol_ntcs.tsv');
    file_path = path.resolve(file_path);

    let outfile = path.resolve(process.env.bic_etl_home, 'cdos/business/nonprofit', 'data_transformed', 'sol_typ_sol_ntcs.csv');

    if (!fs.existsSync(file_path)) {
      log.error("Folder " + file_path + " does not exist to load TSV files for transform.");
        return;
    }

    transform_purpose(file_path, outfile); // Executes the processing
}

let header_columns = [
    "sols_notice_id",
    "ce_name",
    "ps_name",
    "sol_type_dscrp"
];

/*
 */
function transformation(row) {
  let sol_notices_id = 'Sols Notice Id';
  for(let key in row) {
    if(key.indexOf('Sols Notice Id') > -1) {
        sol_notices_id = key;
    }
  }

    let tRow                   = {};
    tRow["sols_notice_id"]     = row["Sols Notice Id"];
    tRow["ce_name"]               = row["Ce Name"];
    tRow["ps_name"]               = row["PS Name"];
    tRow["sol_type_dscrp"] = row["Sol Type Dscrp"];
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
function transform_purpose(file_path, outfile) {
    log.debug("Files to be transformed: " + file_path);
    //Original file
    let input_stream = fs.createReadStream(file_path)
    .on('error', error_handler);
    //Transformed file
    let output_stream = fs.createWriteStream(outfile)
    .on('error', error_handler);
    //Parse input
    const purpose_parser = parse({
        relax: true,
        delimiter: "\t",
        columns: true
    })
    .on('error', error_handler);
    //Transform input
    const purpose_transformer = transform(transformation)
    .on('error', error_handler);
    //New data to output
    const purpose_stringifier = stringify({
        header: true,
        columns: header_columns
    })
    .on('error', error_handler);
    // Connect all streams
    input_stream.pipe(purpose_parser).pipe(purpose_transformer).pipe(purpose_stringifier).pipe(output_stream);

    //Once complete
    output_stream.on('finish', function() {
        log.debug('All items have been processed, final file is at: '+ outfile);
    });
}

