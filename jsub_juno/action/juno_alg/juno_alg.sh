#!/bin/bash



# setup JUNO environment
juno_top=$JSUB_JUNO_top
export CMTCONFIG='amd64_linux26'


source $juno_top/../../contrib/gcc/*/bashrc
source $juno_top/../../contrib/binutils/*/bashrc
source $juno_top/../../../*/contrib/compat/bashrc

#can't run pushd/popd cmds in the JUNO setup script
#source $juno_top/setup.sh
cp $juno_top/setup.sh .
org_dir=`pwd`
sed -i 's/popd.*/cd $JUNOTOP/' ./setup.sh
sed -i 's/>& .*//' ./setup.sh
sed -i 's/pushd/cd/' ./setup.sh
sed -i 's/source /source .\//' ./setup.sh
#cat ./setup.sh
source ./setup.sh
cd $org_dir

#copy so files and job config from input common folder to ./
cp ${JSUB_input_common_dir}/* .

jobConfig=$JSUB_jobConfig
jobConfig=${jobConfig##*/}
soFile=$JSUB_soFile


# plan a: remove all loadDll, append them after import Sniper
#sed -i '/loadDll/d' $jobConfig
#sflist=(${soFile//,/ })
#for sf in ${sflist[@]}
#do
#	sf=${sf##*/}
#	sed -i '/LOAD_DLL/a Sniper.loadDll('"'./"$sf"'"')' $jobConfig
#done 
#sed -i '/LOAD_DLL/d' $jobConfig

# plan b: redirect dll to ./
sed -i "s/loadDll(.*\//loadDll('.\//g" $jobConfig
sed -i 's/.so"/.soTaGrEpLaCe/g' $jobConfig	# to avoid '/" discrepancy
sed -i "s/TaGrEpLaCe/'/" $jobConfig


for idx in `seq 0 30`; do
	eval rtext='$JSUB_alg_rtext_'$idx
	eval textr='$JSUB_alg_textr_'$idx
	if [  ${#rtext} -gt 0 ]; then
		# text replacement
		echo $rtext| sed 's/\//\\\//g' > rtext0
		rtext=`cat rtext0`
		rm rtext0
		echo $textr| sed 's/\//\\\//g' > textr0
		textr=`cat textr0`
		rm textr0
		sed -i 's/'$rtext'/'$textr'/g' $jobConfig
	fi
done

python $jobConfig

exit $?
