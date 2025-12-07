cd ../..


curl -X POST "http://localhost:8086/api/v1/service-catalog/import" \
     -H "accept: application/json" \
     -H "Content-Type: multipart/form-data" \
     -F "file=@static/data/service_catalog.json"

#     -F "file=@static/data/kosodate_and_kyoiku_service_catalog.mini.json"
