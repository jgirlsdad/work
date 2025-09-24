require('dotenv').config({path: __dirname + '/../../.env'});
const fs = require('fs');
const path = require('path');
const moment = require('moment');
const find = require('find');
const custom_log = require(path.join(process.env.bic_etl_home, 'general/scripts/custom_log.js'));
const sg_mail  = require('@sendgrid/mail');
const zip = new require('node-zip')();
const bunyan = require('bunyan');

let log = {};
custom_log.setup("cleanup", function(custom_logger) {
  log = custom_logger;
});

function initiate() {

}

let delimiter = '; ';
let path_delimiter = '/';
if(process.platform === 'win32') {
  delimiter = ' && ';
  path_delimiter = '\\';
}

const log_path = path.join(process.env.bic_etl_home, 'general', 'logs', 'log.json');
const cron_log_path = path.join(process.env.bic_etl_home, 'general', 'logs', 'cron.log');
try {
  let cron_read = fs.createReadStream(cron_log_path);
  cron_read.on('data', (data) => {
    try {
      let cron_log = data.toString();
      if(cron_log.length < 1) {
        return true;
      }
      job_errors['CRON'] = [cron_log];
      fs.renameSync(cron_log_path, cron_log_path + '.' + new Date().toISOString());
    } catch(e) {
      job_errors['Generic Cron error'] = e;
    }
  })
} catch(e) {
  // No cron file, ignore
}


let api_key = process.env.sendgrid_api_key;
sg_mail.setApiKey(api_key);

let read = fs.createReadStream(log_path);
let full_log = '';
let summary = {};
let datasets = [];
let job_errors = {};
let job_warnings = {};
let time = {
  start_time: '3000-06-27T13:18:34.568Z',
  end_time: '2000-06-27T13:18:34.568Z'
}

function parse_data(data) {
  full_log = data.toString('base64');
	let lines = data.toString().split("\n");
  summary.log_length = lines.length;
	lines.forEach(function(line) {
    try {
      let json_line = JSON.parse(line);

      if(moment(json_line.time) < moment(time.start_time)) {
        time.start_time = moment(json_line.time);
      }
      if(moment(json_line.time) > moment(time.end_time)) {
        time.end_time = moment(json_line.time);
      }

      let dataset_title = datasets.filter(function(d) {
        return d == json_line.name;
      });
      if(dataset_title.length < 1) {
        datasets.push(json_line.name);
      }
      if(json_line.level === 40) {
        if(!job_warnings[json_line.name]) {
          job_warnings[json_line.name] = [];
        }
        job_warnings[json_line.name].push(json_line.msg);
      }
      if(json_line.level === 50) {
        if(!job_errors[json_line.name]) {
          job_errors[json_line.name] = [];
        }
        job_errors[json_line.name].push(json_line.msg);
      }
    } catch(e) {
      // Empty line at end of file, ignore
    }
	});
}

function build_summary() {
  let html = '<p>This server is maintained by Colorado OIT, and is referenced under IP: 165.127.62.8' +
	'<br>If you have received this message in error, the email list can be found in the code general/scripts/cleanup.js</br></p>' +
	'<p>The summary of the last day\'s ETL processes is as follows:</p>';

  html += '<p><b>There were {{job_errors_length}} datasets with errors logged.</b></p>';

  let job_errors_length = 0, job_fail_logs_length = 0;
  for(key in job_errors) {
    job_errors_length++;
    html += '<p><b>' + key + ' had the following errors:</b></p><ul>';
    for(var i=0; i<job_errors[key].length; i++) {
      job_fail_logs_length++;
      html += '<li>' + job_errors[key][i] + '</li>';
    }
    html += '</ul>';
  }
  html = html.replace('{{job_errors_length}}', job_errors_length);

  html += '<p><b>There were {{job_warnings_length}} datasets with warnings logged.</b></p>';

  let job_warnings_length = 0;
  for(key in job_warnings) {
    job_warnings_length++;
    html += '<p><b>' + key + ' had the following warnings:</b></p><ul>';
    for(var i=0; i<job_warnings[key].length; i++) {
      job_fail_logs_length++;
      html += '<li>' + job_warnings[key][i] + '</li>';
    }
    html += '</ul>';
  }
  html = html.replace('{{job_warnings_length}}', job_warnings_length);

  html += '<p><b>Total number of log entries: ' + summary.log_length + ', with ' + ((summary.log_length-job_fail_logs_length)*100/summary.log_length) + '% successful</b></p>';

  html += '<p>The jobs ran from ' +
  moment(time.start_time).toString() +
  ' to ' + moment(time.end_time).toString() + '</p>';

  html += '<p><b>The titles/suites that were run:</b></p><ul>';
  for(var i=0; i<datasets.length; i++) {
    html += '<li>' + datasets[i] + '</li>'; + '\n';
  }
  html += '</ul>';

  html += '<p>Full log file is attached, and can be found on the BIC maintenance server under $bic_etl_home/general/logs/</p>';

  return {
    html: html,
    subject: 'BIC Maintenance Report - ' + job_errors_length + ' Errors'
  };
}

async function send_email() {
  log.info('Done reading log, prepping email');

  let summary = await build_summary();

  const msg = {
    to: ['bic-help@xentity.com'],
    // to: 'jbrown@xentity.com',
    from: 'No_Reply@Colorado.gov',
    subject: summary.subject,
    html: summary.html,
    attachments: [{
      content: full_log,
      filename: 'log.json',
      type: 'application/json',
      disposition: 'attachment',
      contentId: 'bic_log'
    }]
  };

  log.debug(summary.html);

  sg_mail.send(msg)
  .then(() => {
    log.info('Completed email');
  })
  .catch(error => {
    log.error('Error with sending email: ' + error);
  });
}

read.on('data', parse_data);
read.on('end', send_email);

//Roll up and zip up old log files
function clean_logs() {
  let old_month_logs = find.fileSync(/log_backup_\d+_\d+\.json$/, path.join(process.env.bic_etl_home, 'general', 'logs'));
  old_month_logs.forEach(function(old_log) {
    let file_name = old_log.split(path_delimiter);
    file_name = file_name[file_name.length-1];
    zip.file(file_name, fs.readFileSync(old_log));
    let data = zip.generate({ base64:false, compression: 'DEFLATE' });
    fs.writeFileSync(path.join(process.env.bic_etl_home, 'general', 'logs', file_name + '.zip'), data, 'binary');
  })

  let logs = find.fileSync(/log\.json.?/, path.join(process.env.bic_etl_home, 'general', 'logs'));
  let archive_logs = [];
  const this_month = moment().month();
  for(var i=0; i<logs.length; i++) {
    let stats = fs.statSync(logs[i]);
    if(moment(stats.mtimeMs).month() < this_month) {
      archive_logs.push(logs[i]);
    }
  }
  let full_month_log = '';
  for(var i=0; i<archive_logs.length; i++) {
    full_month_log += fs.readFileSync(archive_logs[i]).toString();
    fs.unlinkSync(archive_logs[i]);
  }
  let month_log_path = path.join(process.env.bic_etl_home, 'general', 'logs');
  let today = moment();
  let file_name = 'log_backup_' + today.year() + '_' + (today.month()) + '.json';
  month_log_path = path.join(month_log_path, file_name);
  fs.writeFileSync(month_log_path, full_month_log);
}

if(moment().date() === 2) {
  clean_logs();
}
