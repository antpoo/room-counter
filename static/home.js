var socket = io();

// Event handler for new connections.
// The callback function is invoked when a connection with the
// server is established.
socket.on('connect', function() {
    socket.emit('my_event', {data: 'I\'m connected!'});
});


// on receipt of the people count
socket.on('counter', function(msg) {

    // get the count as a number
    var num = Number(msg.count);
    console.log('Received count:', num);

    // handle NaN error
    if (isNaN(num)) {
        console.error('Invalid count received:', msg.count);
        return;
    }


    var counterElement = document.getElementById("counter");
    if (!counterElement) {
        console.error('Counter element not found');
        return;
    }

    // update webpage
    if (num === 1) {
        counterElement.innerHTML = "There is 1 person in the room.";
    } else {
        counterElement.innerHTML = "There are " + num + " people in the room.";
    }
});

// refresh the page to update images
socket.on("reload", function(msg) {
    location.reload();
});

