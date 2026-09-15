# Azure deployment template

[Deploy to Azure](https://portal.azure.com/#create/Microsoft.Template/uri/https%3A%2F%2Fraw.githubusercontent.com%2Fgrovs-io%2Fself-host%2Fmain%2Fdeploy%2Fazure%2Fazuredeploy.json)

See the [operator guide](../../docs/deploy/azure.md) for parameters, DNS, login and
removal. This button opens Azure's custom deployment form with `azuredeploy.json`.
It is independent of a Microsoft Marketplace listing.

`main.bicep` is the source. Rebuild the checked-in ARM JSON whenever that file or
`deploy/vm/bootstrap.sh` changes:

```bash
az bicep build --file deploy/azure/main.bicep
python3 -m unittest discover -s tests
```

Compilation and local tests do not validate subscription quotas, regional VM
availability or a live first boot. Marketplace packaging and live verification
are tracked in [the submission plan](../../docs/deploy/marketplaces.md).
