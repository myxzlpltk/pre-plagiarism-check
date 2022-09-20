// Create DB
db = db.getSiblingDB('skripsi');

// Create collection
db.createCollection('method2');
db.createCollection('method5');

// Create index
db.method2.createIndex({ "filename": 1 });
db.method5.createIndex({ "filename": 1 });