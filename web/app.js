import {
  ConnectionState,
  Room,
  RoomEvent,
  Track,
} from "https://esm.sh/livekit-client@2.18.2";

const els = {
  status: document.querySelector("#status"),
  livekitUrl: document.querySelector("#livekitUrl"),
  tenantId: document.querySelector("#tenantId"),
  agentName: document.querySelector("#agentName"),
  roomName: document.querySelector("#roomName"),
  identity: document.querySelector("#identity"),
  connectBtn: document.querySelector("#connectBtn"),
  muteBtn: document.querySelector("#muteBtn"),
  disconnectBtn: document.querySelector("#disconnectBtn"),
  clearBtn: document.querySelector("#clearBtn"),
  transcript: document.querySelector("#transcript"),
  chatForm: document.querySelector("#chatForm"),
  chatInput: document.querySelector("#chatInput"),
  remoteAudio: document.querySelector("#remoteAudio"),
  micMeter: document.querySelector("#micMeter"),
  agentMeter: document.querySelector("#agentMeter"),
};

let room;
let micMuted = false;
let meterTimer;
const transcriptSegments = new Map();

init();

async function init() {
  els.roomName.value = `agent-test-${Math.random().toString(36).slice(2, 8)}`;
  renderEmpty();
  try {
    const res = await fetch("/api/config");
    const config = await res.json();
    els.livekitUrl.value = config.livekitUrl || "";
    els.tenantId.value = config.tenantId || "acme_corp";
    els.agentName.value = config.agentName || "tenant-voice-agent";
  } catch (error) {
    setStatus("Config error", true);
  }
}

els.connectBtn.addEventListener("click", connect);
els.disconnectBtn.addEventListener("click", disconnect);
els.muteBtn.addEventListener("click", toggleMute);
els.clearBtn.addEventListener("click", () => {
  transcriptSegments.clear();
  renderEmpty();
});
els.chatForm.addEventListener("submit", sendText);

async function connect() {
  setStatus("Connecting");
  setBusy(true);
  try {
    const tokenRes = await fetch("/api/token", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        livekitUrl: els.livekitUrl.value,
        room: els.roomName.value,
        identity: els.identity.value,
        tenantId: els.tenantId.value,
        agentName: els.agentName.value,
      }),
    });
    const tokenPayload = await tokenRes.json();
    if (!tokenRes.ok) {
      throw new Error(tokenPayload.error || "Could not create token");
    }

    room = new Room({
      adaptiveStream: true,
      dynacast: true,
    });
    wireRoom(room);

    await room.connect(tokenPayload.url, tokenPayload.token, { autoSubscribe: true });
    await room.startAudio();
    await room.localParticipant.setMicrophoneEnabled(true);
    startMeters();

    setStatus("Live");
    els.connectBtn.disabled = true;
    els.disconnectBtn.disabled = false;
    els.muteBtn.disabled = false;
  } catch (error) {
    console.error(error);
    setStatus(error.message || "Error", true);
    setBusy(false);
  }
}

async function disconnect() {
  stopMeters();
  if (room) {
    await room.disconnect();
    room = undefined;
  }
  els.remoteAudio.srcObject = null;
  els.connectBtn.disabled = false;
  els.disconnectBtn.disabled = true;
  els.muteBtn.disabled = true;
  els.muteBtn.textContent = "Mute";
  micMuted = false;
  setStatus("Idle");
  setBusy(false);
}

async function toggleMute() {
  if (!room) return;
  micMuted = !micMuted;
  await room.localParticipant.setMicrophoneEnabled(!micMuted);
  els.muteBtn.textContent = micMuted ? "Unmute" : "Mute";
}

async function sendText(event) {
  event.preventDefault();
  if (!room || room.state !== ConnectionState.Connected) return;
  const text = els.chatInput.value.trim();
  if (!text) return;
  appendMessage({ speaker: "You", text, kind: "local", id: crypto.randomUUID() });
  els.chatInput.value = "";
  await room.localParticipant.sendText(text, { topic: "lk.chat" });
}

function wireRoom(activeRoom) {
  activeRoom
    .on(RoomEvent.ConnectionStateChanged, (state) => setStatus(state))
    .on(RoomEvent.Disconnected, () => disconnect())
    .on(RoomEvent.ParticipantConnected, (participant) => {
      appendMessage({
        speaker: "System",
        text: `${participant.identity} joined`,
        kind: "system",
        id: crypto.randomUUID(),
      });
    })
    .on(RoomEvent.TrackSubscribed, (track, publication, participant) => {
      if (track.kind === Track.Kind.Audio) {
        const element = track.attach();
        element.autoplay = true;
        element.dataset.participant = participant.identity;
        document.body.appendChild(element);
      }
    })
    .on(RoomEvent.TrackUnsubscribed, (track) => {
      track.detach().forEach((element) => element.remove());
    })
    .on(RoomEvent.TranscriptionReceived, (segments, participant) => {
      for (const segment of segments) {
        const finalValue = segment.final ?? segment.isFinal ?? false;
        const id = segment.id || `${participant?.identity || "unknown"}-${segment.startTime || Date.now()}`;
        transcriptSegments.set(id, {
          id,
          speaker: speakerFor(participant),
          text: segment.text,
          kind: participant?.isLocal ? "local" : "agent",
          interim: !finalValue,
        });
      }
      renderTranscript();
    });

  activeRoom.registerTextStreamHandler("lk.transcription", async (reader, participantInfo) => {
    const text = await reader.readAll();
    if (!text.trim()) return;
    const attrs = reader.info?.attributes || {};
    const id = attrs.lk_segment_id || `${participantInfo.identity}-${Date.now()}`;
    transcriptSegments.set(id, {
      id,
      speaker: participantInfo.identity || "Agent",
      text,
      kind: participantInfo.identity === activeRoom.localParticipant.identity ? "local" : "agent",
      interim: attrs.lk_transcription_final !== "true",
    });
    renderTranscript();
  });
}

function appendMessage(message) {
  transcriptSegments.set(message.id, message);
  renderTranscript();
}

function renderEmpty() {
  els.transcript.innerHTML = '<p class="empty">Connect, allow microphone access, and start talking.</p>';
}

function renderTranscript() {
  const messages = [...transcriptSegments.values()].filter((item) => item.text);
  if (!messages.length) {
    renderEmpty();
    return;
  }
  els.transcript.innerHTML = "";
  for (const message of messages) {
    const node = document.createElement("div");
    node.className = `message ${message.kind || ""} ${message.interim ? "interim" : ""}`;
    const speaker = document.createElement("strong");
    speaker.textContent = message.speaker;
    const text = document.createElement("span");
    text.textContent = message.text;
    node.append(speaker, text);
    els.transcript.appendChild(node);
  }
  els.transcript.scrollTop = els.transcript.scrollHeight;
}

function speakerFor(participant) {
  if (!participant) return "Agent";
  if (participant.isLocal) return "You";
  return participant.name || participant.identity || "Agent";
}

function setStatus(text, error = false) {
  els.status.textContent = text;
  els.status.classList.toggle("live", text === "Live" || text === ConnectionState.Connected);
  els.status.classList.toggle("error", error);
}

function setBusy(isBusy) {
  els.connectBtn.disabled = isBusy;
}

function startMeters() {
  stopMeters();
  meterTimer = window.setInterval(() => {
    const micLevel = localAudioLevel(room);
    const agentLevel = remoteAudioLevel(room);
    els.micMeter.style.width = `${Math.round(micLevel * 100)}%`;
    els.agentMeter.style.width = `${Math.round(agentLevel * 100)}%`;
  }, 120);
}

function stopMeters() {
  if (meterTimer) {
    clearInterval(meterTimer);
    meterTimer = undefined;
  }
  els.micMeter.style.width = "0%";
  els.agentMeter.style.width = "0%";
}

function localAudioLevel(activeRoom) {
  const publication = activeRoom?.localParticipant.getTrackPublication(Track.Source.Microphone);
  return publication?.audioLevel || 0;
}

function remoteAudioLevel(activeRoom) {
  if (!activeRoom) return 0;
  let level = 0;
  activeRoom.remoteParticipants.forEach((participant) => {
    level = Math.max(level, participant.audioLevel || 0);
  });
  return level;
}
