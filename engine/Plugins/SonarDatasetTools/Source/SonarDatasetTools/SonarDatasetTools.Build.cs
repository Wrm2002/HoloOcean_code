using UnrealBuildTool;

public class SonarDatasetTools : ModuleRules
{
	public SonarDatasetTools(ReadOnlyTargetRules Target) : base(Target)
	{
		PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;

		PublicDependencyModuleNames.AddRange(new string[]
		{
			"Core",
			"CoreUObject",
			"Engine",
			"ImageWrapper",
			"Json",
			"RenderCore",
			"RHI"
		});
	}
}
