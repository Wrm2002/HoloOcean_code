// MIT License (c) 2021 BYU FRoStLab see LICENSE file

#pragma once

#include "CoreMinimal.h"
#include "HolodeckSensor.h"

#include "RaycastImagingSonar.generated.h"

/**
 * Imaging-style sonar backed by Unreal collision traces instead of HoloOcean octrees.
 *
 * This sensor is intended for runtime-spawned props and other collidable actors that
 * are visible to UE traces but are not represented in the static sonar octree.
 */
UCLASS(ClassGroup = (Custom), meta = (BlueprintSpawnableComponent))
class HOLODECK_API URaycastImagingSonar : public UHolodeckSensor {
	GENERATED_BODY()

public:
	URaycastImagingSonar();

	virtual void InitializeSensor() override;
	virtual void ParseSensorParms(FString ParmsJson) override;

protected:
	int GetNumItems() override { return RangeBins * AzimuthBins; };
	int GetItemSize() override { return sizeof(float); };

	void TickSensorComponent(
		float						 DeltaTime,
		ELevelTick					 TickType,
		FActorComponentTickFunction* ThisTickFunction) override;

	UPROPERTY(EditAnywhere)
	float RangeMin = 10.0f;

	UPROPERTY(EditAnywhere)
	float RangeMax = 1000.0f;

	UPROPERTY(EditAnywhere)
	float Azimuth = 120.0f;

	UPROPERTY(EditAnywhere)
	float Elevation = 20.0f;

	UPROPERTY(EditAnywhere)
	int32 RangeBins = 512;

	UPROPERTY(EditAnywhere)
	int32 AzimuthBins = 512;

	UPROPERTY(EditAnywhere)
	int32 ElevationSamples = 8;

	UPROPERTY(EditAnywhere)
	int32 TicksPerCapture = 1;

	UPROPERTY(EditAnywhere)
	float Reflectivity = 1.0f;

	UPROPERTY(EditAnywhere)
	float BackgroundNoise = 0.0f;

	UPROPERTY(EditAnywhere)
	float IntensityScale = 100.0f;

	UPROPERTY(EditAnywhere)
	float IntensityRangePower = 2.0f;

	UPROPERTY(EditAnywhere)
	float RangeBias = 0.0f;

	UPROPERTY(EditAnywhere)
	int32 RangeSpreadBins = 1;

	UPROPERTY(EditAnywhere)
	int32 AzimuthSpreadBins = 1;

	UPROPERTY(EditAnywhere)
	float RangeSpread = 0.0f;

	UPROPERTY(EditAnywhere)
	float AzimuthSpread = 0.0f;

	UPROPERTY(EditAnywhere)
	bool ShowDebug = false;

	UPROPERTY(EditAnywhere)
	bool TraceComplex = true;

private:
	void SimulateSonar(float DeltaTime);
	bool TraceBeam(
		const FVector&		   Start,
		const FVector&		   Direction,
		FHitResult&			   HitResult,
		FCollisionQueryParams& TraceParams) const;
	void AddHitToBuffer(const FHitResult& HitResult, const FVector& RayDirection);
	void AccumulateHit(float RangeBin, float AzimuthBin, float Intensity);

	AActor* Parent = nullptr;
	float*	ResultBuffer = nullptr;
	int32	TickCounter = 0;
};
