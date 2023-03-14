// Heroku

const Heroku = require('heroku-client')
const token = "HEROKU TOKEN"
const heroku = new Heroku({ token: token })
var express = require('express');
const app = express()
app.get('/', (req, res) => res.send(""))
app.listen(process.env.PORT || 8003, () => console.log('Running heroku serv'.grey))


///

// Strategy:

const _ = require('lodash')
const axios = require('axios')
const io = require('socket.io-client')

const socket_key = "SOCKET KEY"
const stratname = "FuturesTrackT2"
let socket_client = {}

// BUY SIGNAL

///

const DELAY = 1000

let datalast_1 = 0;
let restart_1 = 0;
let pair_1 = [];
let pos_1 = [];

let datalast_2 = 0;
let restart_2 = 0;
let pair_2 = [];
let pos_2 = [];


process.on('unhandledRejection', (reason, promise) => {
	console.log('Unhandled Rejection at:', promise, 'reason:', reason);
	console.log("restart_1");
	heroku.delete('/apps/leaderboard-track/dynos').then( x => console.log(x) );
});

// Binance Leaderboard API

const got = require('got')

async function getPrice(eUid) {

	let data = null
	let result = null
	
	try {
		
		const url = "https://www.binance.com/bapi/futures/v1/public/future/leaderboard/getOtherPosition"
		const payload = {
			json: {
				encryptedUid: eUid,
				tradeType: "PERPETUAL"
			}
		}
		console.log(eUid);
		const { data } = await got.post(url, payload).json()
		result = data.otherPositionRetList
		
	} catch (e) {
		console.log('[ ERR ] Crashed (Rate limit?) ['+(new Date()).toGMTString()+"]")
		throw(e)
	}
	return result
}

const arrayColumn = (arr, n) => arr.map(x => x[n]);
    
function track1(){
	
	; (async () => {

		//REDACTED: FUTURES ENCRYPTED UIDS
		
		let data = await getPrice("REDACTED: FUTURES ENCRYPTED UIDS");

		if(data){
			
			console.log(data)
			
			if(datalast_1 != data.length){
				
				datalast_1 = data.length;
				console.log('[ OK ] Got update [' + (new Date()).toGMTString() + "]")
				console.log(data);
				console.log(datalast_1);
				
				let pair_new = data.map(d => d["symbol"]);
				let pos_new = data.map(d => d["amount"])
				for (var i=0; i < pos_new.length; i++) pos_new[i] = (pos_new[i]>0) ? 1 : -1;
				
				if(restart_1>0){
						
					// Check open position

					let open_pair = pair_new.filter(x => !pair_1.includes(x));
					let open_pos = pos_new.filter(x => !pos_1.includes(x));

					// Open Position
					if(open_pair !== []){
						if(open_pos > 0){
							console.log("Open LONG "+open_pair);

							const buy_signal = {
								key: socket_key,
								stratname: stratname,
								pair: open_pair[0],
								new: true
							}
							socket_client.emit("buy_signal", buy_signal)
						}
						if(open_pos < 0){
							console.log("Open SHORT "+open_pair);
							
							const sell_signal = {
								key: socket_key,
								stratname: stratname,
								pair: open_pair[0],
								new: true
							}
							socket_client.emit("sell_signal", sell_signal)
						}
					}

					// Check close position

					let close_pair = pair_1.filter(x => !pair_new.includes(x));
					let close_pos = pos_1.filter(x => !pos_new.includes(x));

					// Close Position
					if(close_pair !== []){
						if(close_pos > 0){
							console.log("Close LONG "+close_pair);
							
							const sell_signal = {
								key: socket_key,
								stratname: stratname,
								pair: close_pair[0],
								new: false
							}
							socket_client.emit("sell_signal", sell_signal)
							
						}
						if(close_pos < 0){
							console.log("Close SHORT "+close_pair);
							
							const buy_signal = {
								key: socket_key,
								stratname: stratname,
								pair: close_pair[0],
								new: false
							}
							socket_client.emit("buy_signal", buy_signal)
						}
					}

					console.log("New: " + open_pair + " " + open_pos + " Old: " + close_pair + " " + close_pos);
				
				}
				
				pair_1=pair_new;
				pos_1=pos_new;
			
			}
		}
		
		restart_1++;
		
	})().catch( e => { console.error(e) })

}

setInterval(track1, 100);

//const myTimeout = setTimeout(track2, 2500);
//track2();