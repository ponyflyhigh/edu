// static/js/webrtc.js
document.addEventListener("DOMContentLoaded", function () {
    const socket = io("http://localhost:5000");

    const startCallButton = document.getElementById('start-call');
    const stopCallButton = document.getElementById('stop-call');
    const localVideo = document.getElementById('local-video');
    const remoteVideo = document.getElementById('remote-video');
    const connectionStatus = document.getElementById('connection-status');

    let peerConnection = null;
    let localStream = null;
    let isCaller = false;

    const configuration = {
        iceServers: [
            { urls: 'stun:stun1.l.google.com:19302' },
            { urls: 'stun:stun2.l.google.com:19302' }
        ]
    };

    function createPeerConnection() {
        peerConnection = new RTCPeerConnection(configuration);

        if (localStream) {
            localStream.getTracks().forEach(track => {
                peerConnection.addTrack(track, localStream);
            });
        }

        peerConnection.ontrack = (event) => {
            remoteVideo.srcObject = event.streams[0];
            updateConnectionStatus('已连接');
        };

        peerConnection.onicecandidate = (event) => {
            if (event.candidate) {
                socket.emit('ice-candidate', {
                    to: isCaller ? 'callee' : 'caller',
                    candidate: event.candidate
                });
            }
        };

        peerConnection.onconnectionstatechange = () => {
            const state = peerConnection.connectionState;
            updateConnectionStatus(state);

            if (state === 'failed' || state === 'disconnected' || state === 'closed') {
                stopCall();
            }
        };
    }

    function updateConnectionStatus(status) {
        connectionStatus.textContent = status;
    }

    startCallButton.addEventListener('click', async () => {
        try {
            localStream = await navigator.mediaDevices.getUserMedia({ video: true, audio: true });
            localVideo.srcObject = localStream;
            localVideo.style.opacity = 1;

            createPeerConnection();
            isCaller = true;

            const offer = await peerConnection.createOffer();
            await peerConnection.setLocalDescription(offer);

            setTimeout(() => {
                socket.emit('offer', {
                    to: 'callee',
                    offer: offer,
                    from: 'caller'
                });
            }, 500);

            startCallButton.disabled = true;
            stopCallButton.disabled = false;
            updateConnectionStatus('连接中');
        } catch (error) {
            console.error('获取媒体流错误:', error);
            alert('无法访问摄像头或麦克风');
        }
    });

    stopCallButton.addEventListener('click', stopCall);

    function stopCall() {
        if (peerConnection) {
            peerConnection.close();
            peerConnection = null;
        }

        if (localStream) {
            localStream.getTracks().forEach(track => track.stop());
            localStream = null;
        }

        localVideo.srcObject = null;
        remoteVideo.srcObject = null;
        localVideo.style.opacity = 0;

        startCallButton.disabled = false;
        stopCallButton.disabled = true;
        isCaller = false;
        updateConnectionStatus('未连接');
    }

    socket.on('offer', async (data) => {
        if (!isCaller && !peerConnection) {
            try {
                localStream = await navigator.mediaDevices.getUserMedia({ video: true, audio: true });
                localVideo.srcObject = localStream;
                localVideo.style.opacity = 1;

                createPeerConnection();
                await peerConnection.setRemoteDescription(new RTCSessionDescription(data.offer));

                const answer = await peerConnection.createAnswer();
                await peerConnection.setLocalDescription(answer);

                socket.emit('answer', {
                    to: 'caller',
                    answer: answer,
                    from: 'callee'
                });

                startCallButton.disabled = true;
                stopCallButton.disabled = false;
                updateConnectionStatus('连接中');
            } catch (error) {
                console.error('处理offer错误:', error);
            }
        }
    });

    socket.on('answer', async (data) => {
        if (isCaller && peerConnection) {
            try {
                await peerConnection.setRemoteDescription(new RTCSessionDescription(data.answer));
            } catch (error) {
                console.error('处理answer错误:', error);
            }
        }
    });

    socket.on('ice-candidate', (data) => {
        if (peerConnection) {
            try {
                peerConnection.addIceCandidate(new RTCIceCandidate(data.candidate));
            } catch (error) {
                console.error('添加ICE候选错误:', error);
            }
        }
    });

    console.log("webrtc.js loaded");
});