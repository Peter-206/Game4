"use strict";

const STATES=Object.freeze({CONNECTING:"connecting",SETUP:"setup",LOBBY:"lobby",WAITING:"waiting",ACTIVE:"active-turn",PROMPT:"prompt",SUBMITTED:"submitted",PAUSED:"paused",RECONNECTING:"reconnecting",ENDED:"game-ended"});
const $=selector=>document.querySelector(selector);
const title=$("#state-title"),status=$("#status"),identity=$("#identity"),setup=$("#setup"),action=$("#action"),roll=$("#roll"),join=$("#join"),playerName=$("#player-name"),tokenOptions=$("#token-options"),promptForm=$("#prompt"),promptText=$("#prompt-text"),promptControls=$("#prompt-controls"),submitPrompt=$("#submit-prompt"),rosterPanel=$("#roster-panel"),roster=$("#roster");
const room=new URLSearchParams(location.search).get("room")||"";
const sessionKey=`pizza-box-controller:${room}`;
let controllerSession=loadControllerSession(),socket,selectedToken="",playerId=controllerSession?.playerId||"",turnId=0,activePromptId="",reconnectTimer,reconnectDelay=500,timerInterval,playersById=new Map();

function loadControllerSession(){
  try {
    const value=JSON.parse(localStorage.getItem(sessionKey)||"null");
    return value&&typeof value.playerId==="string"&&typeof value.sessionToken==="string"?value:null;
  } catch { return null; }
}
function saveControllerSession(message){
  controllerSession={playerId:String(message.player_id),sessionToken:String(message.session_token),name:String(message.player.name)};
  playerId=controllerSession.playerId;
  localStorage.setItem(sessionKey,JSON.stringify(controllerSession));
  renderIdentity();
}
function clearControllerSession(){controllerSession=null;playerId="";localStorage.removeItem(sessionKey);renderIdentity();}
function renderIdentity(){identity.hidden=!controllerSession;identity.textContent=controllerSession?`Playing as ${controllerSession.name}`:"";}

export function renderState(state,message=""){
  setup.hidden=state!==STATES.SETUP;
  action.hidden=![STATES.LOBBY,STATES.WAITING,STATES.ACTIVE,STATES.PROMPT,STATES.SUBMITTED,STATES.PAUSED,STATES.RECONNECTING,STATES.ENDED].includes(state);
  promptForm.hidden=state!==STATES.PROMPT;roll.hidden=state===STATES.PROMPT;roll.disabled=state!==STATES.ACTIVE;
  title.textContent=state.split("-").map(word=>word[0].toUpperCase()+word.slice(1)).join(" ");
  status.textContent=message;document.body.dataset.state=state;
}
function send(payload){if(socket?.readyState===WebSocket.OPEN)socket.send(JSON.stringify(payload));}
roll.addEventListener("click",()=>{roll.disabled=true;send({type:"roll",turn_id:turnId});renderState(STATES.SUBMITTED,"Roll sent. Watch the host screen!");});

function renderRoster(players){
  playersById=new Map((players||[]).map(player=>[String(player.player_id),player]));
  const ordered=[...(players||[])];
  roster.replaceChildren(...ordered.map(player=>{const item=document.createElement("li"),name=document.createElement("span"),connection=document.createElement("span"),local=String(player.player_id)===playerId;item.dataset.local=String(local);if(player.is_beer_bitch){const role=document.createElement("strong");role.className="beer-bitch-label";role.textContent="Beer Bitch ";name.append(role);}name.append(document.createTextNode(`${player.name}${local?" (You)":""}`));connection.className="connection";connection.textContent=player.connected===false?"Disconnected":"Connected";item.append(name,connection);return item;}));
  rosterPanel.hidden=!controllerSession||!(players||[]).length;
}
function activePlayerName(value){return playersById.get(String(value))?.name||"Another player";}
function showTokens(tokens){tokenOptions.replaceChildren(...tokens.map(token=>{const button=document.createElement("button");button.type="button";button.textContent=token;button.setAttribute("aria-pressed","false");button.addEventListener("click",()=>{selectedToken=token;tokenOptions.querySelectorAll("button").forEach(item=>item.setAttribute("aria-pressed",String(item===button)));});return button;}));}
function choice(value,labelText){const label=document.createElement("label"),input=document.createElement("input"),span=document.createElement("span");label.className="prompt-choice";input.type="radio";input.name="prompt-response";input.value=value;input.required=true;span.textContent=labelText;label.append(input,span);return label;}
function stopTimerDisplay(){if(timerInterval){clearInterval(timerInterval);timerInterval=undefined;}}
function submitPromptResponse(response){send({type:"event_response",turn_id:turnId,prompt_id:activePromptId,response:String(response)});renderState(STATES.SUBMITTED,"Response submitted. Watch the host screen.");}
function showTimerPrompt(message){
  const button=document.createElement("button"),actionName=String(message.timer_action||"");button.type="button";button.className="timer-action";button.textContent=String(message.timer_label||"Timer");
  const children=[];
  if(actionName==="stopped"){
    const display=document.createElement("p"),started=Number(message.timer_started_at_epoch_ms)||Date.now();display.className="timer-readout";
    const update=()=>{const elapsed=Math.max(0,Date.now()-started);display.textContent=`${(elapsed/1000).toFixed(1)} seconds`;};update();timerInterval=setInterval(update,100);children.push(display);
  }
  button.addEventListener("click",()=>{button.disabled=true;if(actionName==="stopped")stopTimerDisplay();submitPromptResponse(actionName);});children.push(button);promptControls.replaceChildren(...children);submitPrompt.hidden=true;
}
function showLinkPrompt(message){
  const allowedUrl="https://youtu.be/uEXP0iXGwRU",link=document.createElement("a");link.className="external-link";link.textContent=String(message.link_label||"Open Link");link.href=String(message.url)===allowedUrl?allowedUrl:"about:blank";link.target="_blank";link.rel="noopener noreferrer";
  link.addEventListener("click",event=>{if(link.href!==allowedUrl){event.preventDefault();return;}submitPromptResponse("activated");});promptControls.replaceChildren(link);submitPrompt.hidden=true;
}
function showPrompt(message){
  stopTimerDisplay();activePromptId=String(message.prompt_id||"");promptText.textContent=String(message.text||"Choose a response.");submitPrompt.hidden=false;
  if(message.kind==="timer")showTimerPrompt(message);
  else if(message.kind==="link")showLinkPrompt(message);
  else if(message.kind==="text"){const input=document.createElement("input");input.name="prompt-response";input.maxLength=Number(message.max_length)||100;input.required=true;input.autocomplete="off";input.placeholder=message.placeholder||"Type your private response";promptControls.replaceChildren(input);}
  else {const choices=message.kind==="confirmation"?[{value:"confirmed",label:message.confirm_label||"Confirm"}]:(message.choices||[]).map(item=>typeof item==="string"?{value:item,label:item}:{value:String(item.value),label:String(item.label)});promptControls.replaceChildren(...choices.map(item=>choice(item.value,item.label)));}
  renderState(STATES.PROMPT,"Respond privately on this phone.");
}
promptForm.addEventListener("submit",event=>{event.preventDefault();const response=new FormData(promptForm).get("prompt-response");if(response===null||String(response).trim()==="")return;submitPromptResponse(response);});

function handleMessage(message){
  if(message.type==="connected"){reconnectDelay=500;showTokens(message.available_tokens||[]);if(controllerSession)send({type:"reconnect",session_token:controllerSession.sessionToken});else renderState(STATES.SETUP,`Room ${message.room_code}`);}
  else if(message.type==="joined"){saveControllerSession(message);renderState(STATES.LOBBY,`Joined as ${message.player.name}. Waiting for the host.`);}
  else if(message.type==="error"){if(message.error==="invalid_session"){clearControllerSession();rosterPanel.hidden=true;}renderState(controllerSession?STATES.WAITING:STATES.SETUP,message.message||"Could not complete that action.");}
  else if(message.type==="room_state"){
    renderRoster(message.players||[]);
    if(!message.started)renderState(STATES.LOBBY,"Waiting for the host to start.");
    else if([STATES.SETUP,STATES.LOBBY].includes(document.body.dataset.state))renderState(STATES.WAITING,"Game started. Watch the host display.");
  }
  else if(message.type==="player_removed"&&String(message.player_id)===playerId){clearControllerSession();rosterPanel.hidden=true;renderState(STATES.SETUP,message.message||"The host removed you from the lobby. You can join again.");socket.close();}
  else if(message.type==="turn_state"){turnId=message.turn_id;if(message.paused)renderState(STATES.PAUSED,"The host paused the game.");else if(message.active_player_id===playerId&&message.can_roll)renderState(STATES.ACTIVE,"The camera is ready. Roll when you are ready!");else if(message.active_player_id===playerId)renderState(STATES.WAITING,"Your turn—waiting for the camera to settle.");else renderState(STATES.WAITING,`${activePlayerName(message.active_player_id)} is taking their turn.`);}
  else if(message.type==="event_prompt"&&(!message.player_id||message.player_id===playerId))showPrompt(message);
  else if(message.type==="event_resolved"&&(!message.player_id||String(message.player_id)===playerId)){activePromptId="";renderState(STATES.WAITING,"Response accepted. Watch the host display.");}
  else if(message.type==="hot_seat_state"){
    const active=String(message.active_player_id)===playerId,pending=(message.pending_player_ids||[]).map(String).includes(playerId);
    if(message.stage==="collecting"){
      if(active)renderState(STATES.WAITING,`Waiting for Hot Seat questions (${message.received} received).`);
      else if(!pending)renderState(STATES.SUBMITTED,"Your Hot Seat question is in. Watch the host display.");
    } else if(!active)renderState(STATES.WAITING,`${message.active_player_name} is answering Hot Seat questions.`);
  }
  else if(message.type==="pause")renderState(STATES.PAUSED,message.message||"The host paused the game.");
  else if(message.type==="game_end")renderState(STATES.ENDED,message.message||"The game has ended.");
}
function scheduleReconnect(){clearTimeout(reconnectTimer);renderState(STATES.RECONNECTING,"Host disconnected. Retrying…");reconnectTimer=setTimeout(connect,reconnectDelay);reconnectDelay=Math.min(5000,reconnectDelay*2);}
function connect(){if(!room){renderState(STATES.RECONNECTING,"This join link is missing its room token.");return;}clearTimeout(reconnectTimer);const scheme=location.protocol==="https:"?"wss":"ws";socket=new WebSocket(`${scheme}://${location.host}/ws?room=${encodeURIComponent(room)}`);socket.addEventListener("message",event=>{try{handleMessage(JSON.parse(event.data));}catch{renderState(STATES.RECONNECTING,"The host sent an invalid update.");}});socket.addEventListener("close",scheduleReconnect);socket.addEventListener("error",()=>socket.close());}
join.addEventListener("click",()=>{if(!selectedToken){status.textContent="Choose a token first.";return;}send({type:"join",name:playerName.value,token_name:selectedToken});});
window.addEventListener("online",()=>{if(!socket||socket.readyState===WebSocket.CLOSED)connect();});
renderIdentity();renderState(STATES.CONNECTING,"Looking for the host.");connect();
