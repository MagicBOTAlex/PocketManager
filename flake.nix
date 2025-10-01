{
  description = "Python development environment with FastAPI";
  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };
  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = nixpkgs.legacyPackages.${system};
        py = pkgs.python3Packages;

        pocketbase-py = py.buildPythonPackage rec {
          pname = "pocketbase";
          version = "0.15.0";
          src = pkgs.fetchPypi { inherit pname version; sha256 = "sha256-3TqM4g2gmoP14KW1X8ctQIdPViwV2IbV7FoHLjRtP9k="; };
          pyproject = true;
          nativeBuildInputs = [ py.poetry-core ];
          propagatedBuildInputs = with py;
            [ httpx ];
          doCheck = false;
        };
        pythonEnv = pkgs.python3.withPackages (ps:
          with ps; [
            fastapi
            slowapi
            uvicorn
            pydantic
            python-multipart
            jinja2
            python-jose
            passlib
            bcrypt
            python-dotenv
            pocketbase-py
          ]);
        start = pkgs.writeShellApplication {
          name = "start";
          runtimeInputs = [
            pythonEnv
            pkgs.pocketbase
            pkgs.borgbackup
            pkgs.toybox
          ];
          text = ''
            set -euo pipefail
            exec ${pythonEnv}/bin/python main.py
          '';
        };
      in
      {
        devShells.default = pkgs.mkShell {
          buildInputs = with pkgs; [
            pythonEnv
            # Development tools
            python3Packages.pip
            python3Packages.setuptools
            python3Packages.wheel
            python3Packages.virtualenv

            pkgs.borgbackup
            pkgs.pocketbase
            pkgs.toybox
          ];
          shellHook = ''
            # Enable bash completion and case-insensitive completion
            if [ -f ${pkgs.bash-completion}/share/bash-completion/bash_completion ]; then
              source ${pkgs.bash-completion}/share/bash-completion/bash_completion
            fi

            export PYTHONWARNINGS="ignore"

            # Enable case-insensitive completion
            shopt -s nocaseglob
            shopt -s nocasematch
            bind "set completion-ignore-case on"
            bind "set show-all-if-ambiguous on"
            bind "set show-all-if-unmodified on"
            bind "set menu-complete-display-prefix on"

            # Create virtual environment if it doesn't exist
            if [ ! -d "venv" ]; then
              echo "Creating virtual environment..."
              python -m venv venv
            fi

            # Activate virtual environment
            source venv/bin/activate

            # Install pocketbase if not already installed
            if ! python -c "import pocketbase" 2>/dev/null; then
              echo "Installing pocketbase..."
              pip install pocketbase
            fi

            alias run="uvicorn main:app --reload"
            echo "Python FastAPI development environment"
            echo "Python version: $(python --version)"
            echo "Virtual environment: $(which python)"
            echo "FastAPI available with uvicorn server"
          '';
        };
        packages = {
          default = pythonEnv;
          start = start;
        };

        # nix run .#start  (apps.default also works)
        apps = {
          default = {
            type = "app";
            program = "${start}/bin/start";
          };
        };
      });
}
