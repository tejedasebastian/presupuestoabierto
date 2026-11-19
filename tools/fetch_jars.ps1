# Fetches the Delta Lake jars used by the local Spark session (ADR-002).
# Maven coordinates resolved by Ivy hang on some networks; this script
# downloads the jars once so shared/spark.py can mount them via spark.jars.
# CI does not need this: fresh runners resolve spark.jars.packages normally.

$ErrorActionPreference = "Stop"
$jarsDir = Join-Path $PSScriptRoot "jars"
New-Item -ItemType Directory -Force -Path $jarsDir | Out-Null

$artifacts = @(
  @{ Group = "io/delta"; Name = "delta-spark_4.2_2.13"; Version = "4.4.1" },
  @{ Group = "io/delta"; Name = "delta-storage"; Version = "4.4.1" },
  @{ Group = "io/delta"; Name = "delta-kernel-api"; Version = "4.4.1" },
  @{ Group = "io/delta"; Name = "delta-kernel-defaults"; Version = "4.4.1" },
  @{ Group = "io/delta"; Name = "delta-kernel-unitycatalog"; Version = "4.4.1" }
)

foreach ($a in $artifacts) {
  $fileName = "$($a.Name)-$($a.Version).jar"
  $url = "https://repo1.maven.org/maven2/$($a.Group)/$($a.Name)/$($a.Version)/$fileName"
  $out = Join-Path $jarsDir $fileName
  if (Test-Path $out) {
    Write-Output "ok (cached): $fileName"
    continue
  }
  Write-Output "downloading: $fileName"
  Invoke-WebRequest $url -OutFile $out -TimeoutSec 120 -UseBasicParsing
  Write-Output "downloaded: $fileName ($((Get-Item $out).Length) bytes)"
}
