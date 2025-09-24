// Define logging
require('dotenv').config({path: __dirname + '/../../.env'});
const bunyan = require('bunyan');
const path = require('path');
const process = require('process');

function modifiedStream(filePath) {
  return {
    write: log => {
			log = JSON.parse(log);
      log.level = bunyan.nameFromLevel[log.level];
      log.time = new Date().valueOf();
      log._timeStamp = new Date().toISOString();
      log.myProp = "Some Value" + new Date();
			let log_line = log.level + " msg: " + log.msg + " at " + log._timeStamp;
      console.log(log_line);
    }
  };
}

process.on('exit', (e) => {
	if(e !== 0) {
		console.log("Log creation failure, exiting; " + e);
	}
})

async function setup(title, callback) {
	let log = null;
	try {
		let options = {
			name: title,
			streams: [{
				path: path.join(process.env.bic_etl_home, 'general', 'logs', 'log.json'),
				name: title,
				type: 'rotating-file',
				period: '1d',
				count: 90,
				level: 'info'
			}, {
		    name: "console",
		    stream: modifiedStream(),
		    level: 'debug'
		  }]
		}
		log = await bunyan.createLogger(options);
	} catch(e) {
		process.exit(e);
	}
	callback(log);
}

module.exports = {
  setup: setup
}
