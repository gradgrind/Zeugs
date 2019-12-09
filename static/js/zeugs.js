"use strict";

/* Show / hide the sidepanel */
function toggleSidepanel() {
    var sidepanel = document.getElementById("sidepanel0")
    if (sidepanel.style.display === 'block') {
        sidepanel.style.display = 'none';
    } else {
        sidepanel.style.display = 'block';
    }
};

/* Hide the sidepanel */
function closeSidepanel() {
  document.getElementById("mySidepanel").style.display = 'none';
};

/* The rest id probably not wanted (at the moment). */
/* ************************************************ */

function populateSelect(select, items, labels=null) {
    /* labels is a dictionary, the keys being all the items. */
    /* Remove existing options. */
    var last;
    while (last = select.lastChild) select.removeChild(last);
    /* Add new options. */
    let template;
    if (labels) {
        template = function(item) {
            return ('<option value="' + item + '">' + labels[item] + '</option>');
        };
    } else {
        template = function(item) {
            return ('<option>' + item + '</option>');
        };
    };
    for (let item of items) {
        select.insertAdjacentHTML('beforeend',
                template(item));
    };
};

// NEED the translated field names, too!
function populateForm2(form, items, values=null) {
    /* Remove existing fields. */
    var node = form.getElementsByClassName('form2')[0];
    var last;
    while (last = node.lastChild) node.removeChild(last);
    /* Add new fields, with value if supplied. */
    /* like this:
     *      <label for="itemA">First Item</label>
     *      <input id="itemA" type="text" value="xxx">
     */
    const template = function(key, name, val) {
        key = 'K_' + key;
        return ('<label for="' + key + '">' + name 
                    + '</label><input id="' + key + '" type="text" value="'
                    + val + '">');
    };
    // It might be better to have PID non-editable (or even hidden).
    for (let [f, fn] of items) {
        let val = values[f] || '';
        node.insertAdjacentHTML('beforeend',
                template(f, fn, val));
    };
};

function setContents1 (container, data) {
    /* First remove existing items. */
    var node = container.getElementsByTagName('ul')[0];
    var last;
    while (last = node.lastChild) node.removeChild(last);
    /* Now add new items. */
    var template = function(PID, name) {
        return ('<li class="pure-menu-item">'
            + '<div class="pure-menu-link" onclick="return pupilSelected(\''
            + PID + '\');">' + name + '</div></li>'
        );
    };
    
    for (let [PID, name] of data) {
        node.insertAdjacentHTML('beforeend',
                template(PID, name));
/*
<!-- beforebegin -->
<p>
  <!-- afterbegin -->
  foo
  <!-- beforeend -->
</p>
<!-- afterend -->   
*/
        
    };
};
/* Presumably one could alternatively pass the complete HTML to be inserted. */

/* Clear data form. */
function clearForm() {
    document.getElementById("dataform").reset();
};

/* !!! Testing value */
const schoolyear = 2016;

var pupilData;

/* Callback for school-class seleced. */
function klassSelected(select) {
    /* Clear data form. */
    clearForm();
    /* Get the school-class name */
    var z = select.selectedIndex;
    var z1 = select.textContent;
    var klass = select.value
    //alert ("Selected " + klass + ": " + select.options[z].label + "/" + z1);
    
    // Busy screen:
    busy(true);
                
    /* Update list of pupils: fetch this from the server. */
    try {
//        const data = await postData(serverURL + '/textcover/data1', { klass: klass });
//        postData(window.location.href + '/data1', { klass: klass }).then(
//        postData(window.location.host + '/core/pupils',
        postData('core/pupils',
                 { year: schoolyear, klass: klass }).then(
            function(data) {
                // The data from the request is available in a .then block.
//                console.log(JSON.stringify(data)); // JSON-string from `response.json()` call
                pupilData = data;
                setContents1 (document.getElementById("mySidepanel"), data["pupilList"]);
                // Busy screen off:
                busy(false);
            });
    } catch (error) {
        console.error(error);
    }
    
    //setContents1 (document.getElementById("mySidepanel"), jsonpeople["pupilList"]);
};

/* Callback for pupil seleced. */
function pupilSelected(pid) {
    /* Clear data form. */
//    clearForm();
    /* Update form: Actually need to fetch the data first ... */
    let formitems = pupilData["pupilData"][pid];
//    for (var key in formitems) {
        //console.log( key, formitems[key] );
//        document.getElementById(key).value = formitems[key];
//    };
    let form = document.getElementById("dataform");
    populateForm2(form, pupilData["fields"], formitems);
    closeSidepanel();
    return false;
};

/* ************ Initialization ************ */
//var mySelect = document.getElementById("mySelect");
//populateSelect(mySelect, ["09", "09K", "10", "10K", "11", "11K", "12", "12K", "13"]);
/* no class selected */
//mySelect.selectedIndex = -1;
//clearForm();


/* **** Busy screen **** */
function busy(on) {
    if (on) {
        document.getElementById("cover").style.display='flex';
    } else {
        document.getElementById("cover").style.display='none';
    }
};


/* ************ AJAX ************ */
/* 
try {
  const data = await postData('http://example.com/answer', { answer: 42 });
  console.log(JSON.stringify(data)); // JSON-string from `response.json()` call
} catch (error) {
  console.error(error);
}
*/

async function postData(url = '', data = {}) {
  // Default options are marked with *
  const response = await fetch(url, {
    method: 'POST', // *GET, POST, PUT, DELETE, etc.
    mode: 'cors', // no-cors, *cors, same-origin
    cache: 'no-cache', // *default, no-cache, reload, force-cache, only-if-cached
    credentials: 'same-origin', // include, *same-origin, omit
    headers: {
      'Content-Type': 'application/json'
      // 'Content-Type': 'application/x-www-form-urlencoded',
    },
    redirect: 'follow', // manual, *follow, error
    referrer: 'no-referrer', // no-referrer, *client
    body: JSON.stringify(data) // body data type must match "Content-Type" header
  });
  return await response.json(); // parses JSON response into native JavaScript objects
}


/* BUT CONSIDER this form:
 * 
const request = async () => {
    const response = await fetch('https://api.com/values/1');
    const json = await response.json();
    console.log(json);
};

request();
*/


/*
// Build formData object.
let formData = new FormData();
formData.append('name', 'John');
formData.append('password', 'John123');

fetch("api/SampleData",
    {
        body: formData,
        method: "post"
    });
*/
