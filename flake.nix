{
  description = "AWS-syndicate is an Amazon Web Services deployment framework written in Python";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
  };

  outputs = { self, nixpkgs }:
    let
      supportedSystems = [
        "x86_64-linux"
        "aarch64-linux"
        "x86_64-darwin"
        "aarch64-darwin"
      ];
      forAllSystems = nixpkgs.lib.genAttrs supportedSystems;
      nixpkgsFor = forAllSystems (system: import nixpkgs { inherit system; });
    in
    {
      packages = forAllSystems (system:
        let
          pkgs = nixpkgsFor.${system};
          pythonPackages = pkgs.python3Packages;

          requests-aws-sign = pythonPackages.buildPythonPackage rec {
            pname = "requests-aws-sign";
            version = "0.1.6";
            pyproject = true;

            src = pythonPackages.fetchPypi {
              pname = "requests_aws_sign";
              inherit version;
              hash = "sha256-F7LSH3Z332OMviLVMb2ln32+Nkk/D+C49cGbNngLgRE=";
            };

            build-system = with pythonPackages; [
              setuptools
            ];

            dependencies = with pythonPackages; [
              boto3
              requests
            ];

            pythonImportsCheck = [ "requests_aws_sign" ];

            meta = with pkgs.lib; {
              description = "AWS V4 request signing using the requests library";
              homepage = "https://github.com/jmenga/requests-aws-sign";
              license = licenses.isc;
            };
          };

          aws-syndicate = pythonPackages.buildPythonApplication rec {
            pname = "aws-syndicate";
            version = "1.21.3";
            pyproject = true;

            src = ./.;

            build-system = with pythonPackages; [
              setuptools
            ];

            pythonRelaxDeps = true;

            dependencies = with pythonPackages; [
              boto3
              botocore
              click
              pyyaml
              requests
              requests-aws-sign
              tabulate
              tqdm
              troposphere
            ];

            nativeCheckInputs = with pythonPackages; [
              pytestCheckHook
            ];

            preInstallCheck = ''
              export HOME=$(mktemp -d)
            '';

            preCheck = ''
              export HOME=$(mktemp -d)
            '';

            enabledTestPaths = [ "tests/unit" ];

            disabledTests = [
              "test_extracts_names_from_output"
            ];

            pythonImportsCheck = [
              "syndicate"
              "syndicate.core"
            ];

            meta = with pkgs.lib; {
              description = "AWS-syndicate is an Amazon Web Services deployment framework written in Python";
              homepage = "https://github.com/epam/aws-syndicate";
              changelog = "https://github.com/epam/aws-syndicate/blob/master/CHANGELOG.md";
              license = licenses.asl20;
              mainProgram = "syndicate";
            };
          };
        in
        {
          default = aws-syndicate;
          aws-syndicate = aws-syndicate;
        }
      );

      apps = forAllSystems (system: {
        default = {
          type = "app";
          program = "${self.packages.${system}.default}/bin/syndicate";
          meta = {
            description = "AWS-syndicate CLI";
          };
        };
      });

      devShells = forAllSystems (system:
        let
          pkgs = nixpkgsFor.${system};
        in
        {
          default = pkgs.mkShell {
            inputsFrom = [ self.packages.${system}.default ];
            packages = with pkgs.python3Packages; [
              pytest
            ];
          };
        }
      );
    };
}
