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
  .option('-t, --title <n>', 'campaign_reports')
  .option('-e, --ext <n>', '.tsv')
  .parse(process.argv);

program.title = (program.title) ? program.title : 'campaign_reports';
let log = {};
custom_log.setup(program.title, function(custom_logger) {
log = custom_logger;
initiate();
})

function initiate() {
    log.debug("Program Started");

    let ext = (program.ext) ? program.ext : '.tsv';
    let file_path = (program.folderpath) ? program.folderpath : path.join(process.env.bic_etl_home, 'cdos/business/nonprofit', 'data_source', 'sn_cmpgn_rpts.tsv');
    file_path = path.resolve(file_path);

    let outfile = path.resolve(process.env.bic_etl_home, 'cdos/business/nonprofit', 'data_transformed', 'campaign_reports.csv');

    if (!fs.existsSync(file_path)) {
      log.error("Folder " + file_path + " does not exist to load TSV files for transform.");
        return;
    }

    transform_campaign_reports(file_path, outfile); // Executes the processing
}

var ynMap = { "y": 1, "n": 0};
var personTypeObj = {
    "PS": "Paid Solicitor",
    "PFC": "Professional Fundraising Consultant"
}

var header_columns = [
    "solicitationNoticeId",
    "campaignReportId",
    "filingType",
    "filingStatus",
    "campaignDateFiled",
    "charityName",
    "charitySignedDate",
    "solicitorName",
    "solicitorSignedDate",
    "grossContributions",
    "grossTicketSales",
    "grossAdvertisingSales",
    "grossInKind",
    "grossTotal",
    "inKindDescription",
    "grossOther",
    "expenseSalaryCommision",
    "expensePrinting",
    "expensePostage",
    "expenseTelephone",
    "expenseOfficeRental",
    "expenseOfficeExpenses",
    "expenseTotal",
    "expenseAuditoriumRental",
    "expenseEventFee",
    "expenseEventPrinting",
    "expenseEventOther",
    "proceedsNet",
    "proceedsPercentToCharity",
    "isFinancialLocalOnly",
    "bookkeeper",
    "bookkeeperAddress",
    "bookkeeperCity",
    "bookkeeperState",
    "bookkeeperZipcode",
    "activityFlag",
    "comments"
];

/*
	* added column names
	* camel cased names and cities
	* normalized phonenumbers
	* removed violation and organization columns
	* removed any "N/A", "NONE", or "UKNOWN" values
*/
function transformation(row) {
	let sol_notice_id_key = 'Sols Notice Id';
  for(let key in row) {
    if(key.indexOf(sol_notice_id_key) > -1) {
      sol_notice_id_key = key;
    }
  }

    for(var i in row) {
        if (row[i] == "N/A" || row[i].toLowerCase() == "none" || row[i].toLowerCase() == "unknown") {
            row[i] = "";
        }
    }

    var tRow                         			= {};
    tRow["solicitationNoticeId"]   	 = row[sol_notice_id_key];
    tRow["campaignReportId"]         = row['Cmpgn Rpt Id'];
    tRow["filingType"]               = row['Filing Type'];
    tRow["filingStatus"]	         = row['Filing Status'];
    tRow["campaignDateFiled"]        = (row['Nr File Date'] != '') ? moment(row['Nr File Date'], 'YYYYMMDD').format('YYYY-MM-DD') : "";
    tRow["charityName"]              = row['Org Offcl'];
    tRow["charitySignedDate"]        = (row['Nr Cosign Date'] != '') ? moment(row['Nr Cosign Date'], 'YYYYMMDD').format('YYYY-MM-DD') : "";
    tRow["solicitorName"]            = custom_helper.fixCap(row['PS Name']);
    tRow["solicitorSignedDate"]      = (row['Nr Pssign Date'] != '') ? moment(row['Nr Pssign Date'], 'YYYYMMDD').format('YYYY-MM-DD') : "";
    tRow["grossContributions"]       = (row['Nr Gp Cntrbs'].replace) ? row['Nr Gp Cntrbs'].replace(/,/g, "") : row['Nr Gp Cntrbs'];
    tRow["grossTicketSales"]         = (row['Nr Gp Tsales'].replace) ? row['Nr Gp Tsales'].replace(/,/g, "") : row['Nr Gp Tsales'];
    tRow["grossAdvertisingSales"]    = (row['Nr Gp Asales'].replace) ? row['Nr Gp Asales'].replace(/,/g, "") : row['Nr Gp Asales'];
    tRow["grossInKind"]              = (row['Nr Gp Inkind'].replace) ? row['Nr Gp Inkind'].replace(/,/g, "") : row['Nr Gp Inkind'];
    tRow["grossTotal"]               = (row['Nr Tot Fp'].replace) ? row['Nr Tot Fp'].replace(/,/g, "") : row['Nr Tot Fp'];
    tRow["inKindDescription"]        = row['Inkind Dscrp'];
    tRow["grossOther"]               = (row['Nr Gp Othr'].replace) ? row['Nr Gp Othr'].replace(/,/g, "") : row['Nr Gp Othr'];
    tRow["expenseSalaryCommision"]   = (row['Nr Exp Sal'].replace) ? row['Nr Exp Sal'].replace(/,/g, "") : row['Nr Exp Sal'];
    tRow["expensePrinting"]          = (row['Nr Exp Prntng'].replace) ? row['Nr Exp Prntng'].replace(/,/g, "") : row['Nr Exp Prntng'];
    tRow["expensePostage"]           = (row['Nr Exp Post'].replace) ? row['Nr Exp Post'].replace(/,/g, "") : row['Nr Exp Post'];
    tRow["expenseTelephone"]         = (row['Nr Exp Tele'].replace) ? row['Nr Exp Tele'].replace(/,/g, "") : row['Nr Exp Tele'];
    tRow["expenseOfficeRental"]      = (row['Nr Exp Rntl'].replace) ? row['Nr Exp Rntl'].replace(/,/g, "") : row['Nr Exp Rntl'];
    tRow["expenseOfficeExpenses"]    = (row['Nr Exp Off'].replace) ? row['Nr Exp Off'].replace(/,/g, "") : row['Nr Exp Off'];
    tRow["expenseTotal"]             = (row['Nr Tot Exp'].replace) ? row['Nr Tot Exp'].replace(/,/g, "") : row['Nr Tot Exp'];
    tRow["expenseAuditoriumRental"]  = (row['Nr Dex Aud'].replace) ? row['Nr Dex Aud'].replace(/,/g, "") : row['Nr Dex Aud'];
    tRow["expenseEventFee"]          = (row['Nr Dex Pfees'].replace) ? row['Nr Dex Pfees'].replace(/,/g, "") : row['Nr Dex Pfees'];
    tRow["expenseEventPrinting"]     = (row['Nr Dex Prntng'].replace) ? row['Nr Dex Prntng'].replace(/,/g, "") : row['Nr Dex Prntng'];
    tRow["expenseEventOther"]        = (row['Nr Dex Other'].replace) ? row['Nr Dex Other'].replace(/,/g, "") : row['Nr Dex Other'];
    tRow["proceedsNet"]              = (row['Nr Net Chrty'].replace) ? row['Nr Net Chrty'].replace(/,/g, "") : row['Nr Net Chrty'];
    tRow["proceedsPercentToCharity"] = (row['Nr Prcnt Chrty'].replace) ? row['Nr Prcnt Chrty'].replace(/,/g, "") : row['Nr Prcnt Chrty'];
    tRow["isFinancialLocalOnly"]     = ynMap[row['Nr Co Only Flg'].toLowerCase()];
    tRow["bookkeeper"]               = row['Nr Bkkpr Name'];
    tRow["bookkeeperAddress"]        = row['Nr Bkkpr Addr'];
    tRow["bookkeeperCity"]           = row['Nr Bkkpr City'];
    tRow["bookkeeperState"]          = row['Nr Bkkpr State'];
    tRow["bookkeeperZipcode"]        = row['Nr Bkkpr Zip'];
    tRow["activityFlag"]             = ynMap[row['Nr No Act Flg'].toLowerCase()];
    tRow["comments"]                 = row['Comments'];
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
function transform_campaign_reports(file_path, outfile) {
    log.debug("Files to be transformed: " + file_path);
    //Original file
    let input_stream = fs.createReadStream(file_path)
    .on('error', error_handler);
    //Transformed file
    let output_stream = fs.createWriteStream(outfile)
    .on('error', error_handler);
    //Parse input
    const campaign_reports_parser = parse({
        relax: true,
        delimiter: "\t",
        columns: true
    })
    .on('error', error_handler);
    //Transform input
    const campaign_reports_transformer = transform(transformation)
    .on('error', error_handler);
    //New data to output
    const campaign_reports_stringifier = stringify({
        header: true,
        columns: header_columns
    })
    .on('error', error_handler);
    // Connect all streams
    input_stream.pipe(campaign_reports_parser).pipe(campaign_reports_transformer).pipe(campaign_reports_stringifier).pipe(output_stream);

    //Once complete
    output_stream.on('finish', function() {
        log.debug('All items have been processed, final file is at: '+ outfile);
    });
}