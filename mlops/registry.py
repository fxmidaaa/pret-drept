"""Explicit local registration, alias assignment and export; no automatic promotion."""

import argparse
import json
import shutil
import tempfile
from pathlib import Path

from mlops.files import write_json
from mlops.models import verify_files
from mlops.track import local_client


def register(run_id: str, store: Path, name: str | None = None):
    import mlflow
    from mlflow.exceptions import MlflowException

    client = local_client(store)
    run = client.get_run(run_id)
    if run.info.status != "FINISHED" or run.data.tags.get("model_ready") != "true":
        raise ValueError(
            "Register a finished run with a saved predictor; scores alone are insufficient."
        )
    dataset = run.data.tags["dataset"]
    name = name or f"pret-drept-{dataset}"
    try:
        client.create_registered_model(
            name, tags={"dataset": dataset, "target_unit": "EUR/month"}
        )
    except MlflowException as exc:
        if exc.error_code != "RESOURCE_ALREADY_EXISTS":
            raise
    if client.get_registered_model(name).tags.get("dataset") != dataset:
        raise ValueError(
            "Synthetic and private models must have separate registry names."
        )
    for version in client.search_model_versions(f"name = '{name}'"):
        if version.run_id == run_id:
            return version
    return mlflow.register_model(
        run.data.tags["model_uri"],
        name,
        tags={"model_type": run.data.tags["model_type"], "dataset": dataset},
    )


def set_alias(name: str, version: str, alias: str, store: Path) -> None:
    client = local_client(store)
    model = client.get_model_version(name, version)
    if model.status != "READY":
        raise ValueError("Assign aliases only to ready model versions.")
    client.set_registered_model_alias(name, alias, version)


def export_model(
    name: str,
    output: Path,
    store: Path,
    *,
    version: str | None = None,
    alias: str | None = None,
) -> dict:
    import mlflow
    from mlflow.models import Model

    if (version is None) == (alias is None):
        raise ValueError("Choose exactly one version or alias.")
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite {output}.")
    client = local_client(store)
    selected = (
        client.get_model_version_by_alias(name, alias)
        if alias
        else client.get_model_version(name, version)
    )
    # Pin the resolved version so an alias change cannot affect this export.
    uri = f"models:/{name}/{selected.version}"
    with tempfile.TemporaryDirectory() as temporary:
        downloaded = Path(
            mlflow.artifacts.download_artifacts(artifact_uri=uri, dst_path=temporary)
        )
        metadata = Model.load(str(downloaded / "MLmodel"))
        data = downloaded / metadata.flavors["python_function"]["data"]
        specification = json.loads((data / "model.json").read_text())
        verify_files(data, specification)
        identity = {
            "name": name,
            "version": selected.version,
            "run_id": selected.run_id,
            "model_uri": uri,
        }
        shutil.copytree(downloaded, output)
        write_json(output / "registry.json", identity)
    return identity


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Manage the local MLflow model registry."
    )
    parser.add_argument("--store", type=Path, default=Path(".mlflow"))
    commands = parser.add_subparsers(dest="command", required=True)
    registration = commands.add_parser("register", help="Register a tracked predictor.")
    registration.add_argument("run_id")
    registration.add_argument("--name")
    listing = commands.add_parser(
        "list", help="List versions, aliases and evaluation metrics."
    )
    listing.add_argument("name")
    assignment = commands.add_parser(
        "alias", help="Explicitly assign or move an alias."
    )
    assignment.add_argument("name")
    assignment.add_argument("version")
    assignment.add_argument("alias", nargs="?", default="champion")
    export = commands.add_parser(
        "export", help="Export a complete predictor to a new directory."
    )
    export.add_argument("name")
    selection = export.add_mutually_exclusive_group(required=True)
    selection.add_argument("--version")
    selection.add_argument("--alias")
    export.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "register":
        version = register(args.run_id, args.store, args.name)
        print(f"models:/{version.name}/{version.version}")
    elif args.command == "alias":
        set_alias(args.name, args.version, args.alias, args.store)
        print(f"{args.name}@{args.alias} -> {args.version}")
    elif args.command == "export":
        print(
            json.dumps(
                export_model(
                    args.name,
                    args.output,
                    args.store,
                    version=args.version,
                    alias=args.alias,
                )
            )
        )
    else:
        client = local_client(args.store)
        for version in client.search_model_versions(f"name = '{args.name}'"):
            run = client.get_run(version.run_id)
            print(
                json.dumps(
                    {
                        "version": version.version,
                        "aliases": version.aliases,
                        "model_type": run.data.tags.get("model_type"),
                        "metrics": run.data.metrics,
                        "run_id": version.run_id,
                    }
                )
            )


if __name__ == "__main__":
    main()
